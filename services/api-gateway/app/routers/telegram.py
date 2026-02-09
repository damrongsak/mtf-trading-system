from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import hmac
import hashlib
import httpx
import logging
import os

from app.database import get_db
from app.models import TelegramChatMapping, User, UserPreferences
from app.security import get_current_user
from app.utils.encryption import encrypt_token, decrypt_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram", tags=["telegram"])

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_SECRET_TOKEN = os.getenv("TELEGRAM_WEBHOOK_SECRET", "mtf_olympus_webhook_secret")
AI_ANALYST_URL = os.getenv("AI_ANALYST_URL", "http://ai-analyst:8001")


class TelegramUpdate(BaseModel):
    """Telegram webhook update structure"""
    update_id: int
    message: dict | None = None


class LinkTelegramRequest(BaseModel):
    """Request to link Telegram chat_id to user account"""
    chat_id: int


class LinkTelegramResponse(BaseModel):
    """Response after linking Telegram"""
    success: bool
    message: str
    chat_id: int


class ConfigureBotRequest(BaseModel):
    """Request to configure Telegram bot token"""
    bot_token: str


class ConfigureBotResponse(BaseModel):
    """Response after configuring bot token"""
    success: bool
    message: str
    bot_username: str | None = None


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Receives incoming messages from Telegram Bot API.
    Validates signature, maps chat_id to user_id, and forwards to AI Analyst.
    """
    # 1. Validate Telegram signature
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret_token != TELEGRAM_SECRET_TOKEN:
        logger.warning(f"Invalid Telegram webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # 2. Parse incoming update
    try:
        body = await request.json()
        update = TelegramUpdate(**body)
    except Exception as e:
        logger.error(f"Failed to parse Telegram update: {e}")
        return {"ok": True}  # Return 200 to Telegram to avoid retries
    
    # 3. Extract message
    if not update.message:
        return {"ok": True}
    
    chat_id = update.message.get("chat", {}).get("id")
    message_id = update.message.get("message_id")  # Extract message_id for reply threading
    text = update.message.get("text", "")
    
    if not chat_id or not text:
        return {"ok": True}
    
    # 4. Lookup user_id from chat_id
    mapping = db.query(TelegramChatMapping).filter(
        TelegramChatMapping.chat_id == chat_id,
        TelegramChatMapping.is_active == True
    ).first()
    
    if not mapping:
        # User hasn't linked their Telegram yet
        await send_telegram_message(
            chat_id,
            "⚠️ **Account Not Linked**\n\n"
            "Please link your Telegram account via the MTF Olympus web dashboard first.\n\n"
            "Go to: Settings → Integrations → Link Telegram"
        )
        return {"ok": True}
    
    # 5. Get user details
    user = db.query(User).filter(User.id == mapping.user_id).first()
    if not user:
        logger.error(f"User {mapping.user_id} not found for chat_id {chat_id}")
        return {"ok": True}
    
    # 6. Forward to AI Analyst (async, don't wait for response)
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{AI_ANALYST_URL}/api/v1/ai/chat/sessions/message",
                json={
                    "message": text,
                    "user_id": user.username,
                    "reply_via_telegram": True,
                    "telegram_chat_id": chat_id,
                    "telegram_message_id": message_id  # For reply threading
                }
            )
            
            if response.status_code != 200:
                logger.error(f"AI Analyst returned {response.status_code}: {response.text}")
                await send_telegram_message(
                    chat_id,
                    "❌ Sorry, I encountered an error processing your request. Please try again."
                )
    except Exception as e:
        logger.error(f"Failed to forward message to AI Analyst: {e}")
        await send_telegram_message(
            chat_id,
            "❌ Service temporarily unavailable. Please try again in a moment."
        )
    
    return {"ok": True}


@router.post("/link", response_model=LinkTelegramResponse)
async def link_telegram(
    request: LinkTelegramRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Links a Telegram chat_id to the authenticated user's account.
    """
    # Check if this chat_id is already linked
    existing = db.query(TelegramChatMapping).filter(
        TelegramChatMapping.chat_id == request.chat_id
    ).first()
    
    if existing:
        if existing.user_id == current_user.id:
            return LinkTelegramResponse(
                success=True,
                message="This Telegram account is already linked to your account.",
                chat_id=request.chat_id
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="This Telegram account is already linked to another user."
            )
    
    # Create new mapping
    mapping = TelegramChatMapping(
        user_id=current_user.id,
        chat_id=request.chat_id,
        is_active=True
    )
    db.add(mapping)
    db.commit()
    
    # Send confirmation to Telegram
    await send_telegram_message(
        request.chat_id,
        f"✅ **Account Linked Successfully**\n\n"
        f"Your Telegram is now linked to: **{current_user.username}**\n\n"
        f"You can now chat with the MTF Olympus AI Analyst directly here!"
    )
    
    return LinkTelegramResponse(
        success=True,
        message="Telegram account linked successfully!",
        chat_id=request.chat_id
    )


@router.post("/configure", response_model=ConfigureBotResponse)
async def configure_bot_token(
    request: ConfigureBotRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Configure user's personal Telegram bot token.
    Validates the token with Telegram API before storing.
    """
    # 1. Validate bot token by calling Telegram API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.telegram.org/bot{request.bot_token}/getMe"
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid bot token. Please check your token and try again."
                )
            
            bot_info = response.json()
            if not bot_info.get("ok"):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid bot token. Please check your token and try again."
                )
            
            bot_username = bot_info.get("result", {}).get("username", "Unknown")
    except httpx.RequestError as e:
        logger.error(f"Failed to validate bot token: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to validate bot token. Please try again."
        )
    
    # 2. Encrypt and store the token
    encrypted_token = encrypt_token(request.bot_token)
    
    # 3. Get or create user preferences
    prefs = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    if not prefs:
        prefs = UserPreferences(user_id=current_user.id)
        db.add(prefs)
    
    prefs.telegram_bot_token = encrypted_token
    db.commit()
    
    logger.info(f"User {current_user.username} configured Telegram bot: @{bot_username}")
    
    return ConfigureBotResponse(
        success=True,
        message=f"Telegram bot @{bot_username} configured successfully!",
        bot_username=bot_username
    )


@router.get("/status")
async def telegram_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if the current user has linked their Telegram account and configured a bot.
    """
    mapping = db.query(TelegramChatMapping).filter(
        TelegramChatMapping.user_id == current_user.id,
        TelegramChatMapping.is_active == True
    ).first()
    
    prefs = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    has_bot_token = bool(prefs and prefs.telegram_bot_token)
    
    if mapping:
        return {
            "linked": True,
            "chat_id": mapping.chat_id,
            "linked_at": mapping.linked_at.isoformat(),
            "bot_configured": has_bot_token
        }
    else:
        return {
            "linked": False,
            "bot_configured": has_bot_token
        }


async def send_telegram_message(chat_id: int, text: str):
    """
    Helper function to send a message via Telegram Bot API.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                logger.error(f"Telegram API error: {response.text}")
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
