"""
Telegram Long Polling Service (Multi-Bot Manager)
================================================
Replaces Webhook-based Telegram message reception with Long Polling.
Supports both a system-wide bot and personal user bots (BYOK).

Flow:
  Manager syncs bots from DB → starts/stops _bot_worker() tasks
  Worker getUpdates → _process_update()
    → Forward to AI Analyst with user JWT
"""

import asyncio
import logging
import os
import httpx
from sqlalchemy.orm import Session
from typing import Optional, Dict, Set
from uuid import UUID

from app.utils.encryption import decrypt_token
from app.models import UserPreferences, TelegramChatMapping, User
from app.security import create_access_token

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
AI_ANALYST_URL = os.getenv("AI_ANALYST_URL", "http://ai-analyst:8001")
TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramPollingService:
    """Background manager for multiple Telegram bot polling workers."""

    def __init__(self, db_session_factory, bot_token: str = "", ai_analyst_url: str = ""):
        self.db_session_factory = db_session_factory
        self.system_bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.ai_analyst_url = ai_analyst_url or AI_ANALYST_URL
        
        self._manager_task: Optional[asyncio.Task] = None
        self._user_tasks: Dict[Optional[UUID], asyncio.Task] = {}
        self._user_tokens: Dict[Optional[UUID], str] = {}
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self):
        """Start the manager loop which synchronizes bot workers."""
        self._running = True
        self._manager_task = asyncio.create_task(self._manager_loop())
        logger.info("✅ Telegram Multi-Bot Polling Manager started")

    async def stop(self):
        """Gracefully stop the manager and all bot workers."""
        self._running = False
        
        if self._manager_task:
            self._manager_task.cancel()
            
        # Cancel all workers
        for task in self._user_tasks.values():
            task.cancel()
            
        # Wait for all tasks to complete
        tasks = list(self._user_tasks.values())
        if self._manager_task:
            tasks.append(self._manager_task)
            
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
        self._user_tasks.clear()
        self._user_tokens.clear()
        logger.info("🛑 Telegram Polling Manager stopped.")

    # ------------------------------------------------------------------
    # Manager Logic
    # ------------------------------------------------------------------

    async def _manager_loop(self):
        """Periodically syncs bots from the database (heartbeat)."""
        while self._running:
            try:
                await self._sync_bots()
            except Exception as e:
                logger.error(f"Error in manager sync loop: {e}", exc_info=True)
            
            # Sleep for a minute before next sync
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break

    async def _sync_bots(self):
        """
        Looks up UserPreferences for tokens and starts/stops workers as needed.
        """
        def get_bot_prefs():
            db: Session = self.db_session_factory()
            try:
                # 1. Find all users with personal bot tokens
                return db.query(UserPreferences).filter(
                    UserPreferences.telegram_bot_token.isnot(None)
                ).all()
            finally:
                db.close()

        try:
            prefs_list = await asyncio.to_thread(get_bot_prefs)
            
            active_personal_user_ids = set()
            personal_tokens = set()
            for prefs in prefs_list:
                try:
                    token = decrypt_token(prefs.telegram_bot_token)
                    if token:
                        await self._ensure_worker(prefs.user_id, token)
                        active_personal_user_ids.add(prefs.user_id)
                        personal_tokens.add(token)
                except Exception as e:
                    logger.error(f"Failed to load personal bot for user {prefs.user_id}: {e}")

            # 2. Ensure System Bot is running ONLY if it's not already covered by a personal worker
            if self.system_bot_token:
                if self.system_bot_token in personal_tokens:
                    if None in self._user_tasks:
                        logger.info("Stopping System worker because it's now handled by a personal worker")
                        await self._stop_worker(None)
                else:
                    await self._ensure_worker(None, self.system_bot_token)
            
            # 3. Stop workers for users who removed their tokens
            current_workers = list(self._user_tasks.keys())
            for user_id in current_workers:
                if user_id is not None and user_id not in active_personal_user_ids:
                    logger.info(f"Stopping worker for user {user_id} (token removed)")
                    await self._stop_worker(user_id)
        except Exception as e:
            logger.error(f"Sync bots failed: {e}")

    async def _ensure_worker(self, user_id: Optional[UUID], token: str):
        """Start or restart a worker if the token has changed."""
        current_token = self._user_tokens.get(user_id)
        
        # If already running with same token, do nothing
        if current_token == token and user_id in self._user_tasks and not self._user_tasks[user_id].done():
            return

        # If token changed or not running, restart it
        if user_id in self._user_tasks:
            await self._stop_worker(user_id)
            
        self._user_tokens[user_id] = token
        self._user_tasks[user_id] = asyncio.create_task(self._bot_worker(user_id, token))
        
        bot_desc = "System" if user_id is None else f"User {user_id}"
        logger.info(f"🚀 Started Telegram polling worker for {bot_desc} bot")

    async def _stop_worker(self, user_id: Optional[UUID]):
        """Stop a specific worker task."""
        task = self._user_tasks.pop(user_id, None)
        self._user_tokens.pop(user_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    # ------------------------------------------------------------------
    # Worker Loop (Individual Bot)
    # ------------------------------------------------------------------

    async def _bot_worker(self, user_id: Optional[UUID], token: str):
        """
        Individual long-polling loop for a specific bot token.
        """
        # 1. Delete webhook so polling works
        await self._delete_webhook(token)
        
        offset = 0
        url = f"{TELEGRAM_API_BASE}/bot{token}/getUpdates"
        bot_desc = "System" if user_id is None else f"User {user_id}"

        while self._running:
            try:
                params = {
                    "timeout": 30,
                    "offset": offset,
                    "allowed_updates": ["message"],
                }
                async with httpx.AsyncClient(timeout=40.0) as client:
                    resp = await client.get(url, params=params)

                if resp.status_code == 401:
                    logger.error(f"❌ Unauthorized (401) for {bot_desc} bot. Stopping worker.")
                    break
                
                if resp.status_code != 200:
                    logger.warning(f"⚠️ {bot_desc} getUpdates error {resp.status_code}")
                    await asyncio.sleep(5)
                    continue

                data = resp.json()
                if not data.get("ok"):
                    logger.error(f"⚠️ {bot_desc} API error: {data}")
                    await asyncio.sleep(5)
                    continue

                updates = data.get("result", [])
                for update in updates:
                    offset = update["update_id"] + 1
                    await self._process_update(update, token, user_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"💥 {bot_desc} loop error: {e}")
                await asyncio.sleep(5)

    async def _delete_webhook(self, token: str):
        url = f"{TELEGRAM_API_BASE}/bot{token}/deleteWebhook"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(url, json={"drop_pending_updates": False})
        except Exception as e:
            logger.debug(f"Webhook deletion failed (non-critical): {e}")

    async def _process_update(self, update: dict, token: str, bot_owner_id: Optional[UUID]):
        """
        Process update from either a system bot or a personal bot.
        """
        message = update.get("message")
        if not message: return

        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        thread_id = message.get("message_thread_id")  # For Telegram Forums
        text = message.get("text", "").strip()
        if not chat_id or not text: return

        def get_user_and_auto_link():
            db: Session = self.db_session_factory()
            try:
                user = None
                if bot_owner_id:
                    # 1. Personal Bot -> Message always belongs to the owner
                    user = db.query(User).filter(User.id == bot_owner_id).first()
                    if user:
                        # Sync chat_id in mappings for this user if it's new
                        self._auto_link_chat(db, user.id, chat_id)
                else:
                    # 2. System Bot -> Lookup user by chat_id
                    mapping = db.query(TelegramChatMapping).filter(
                        TelegramChatMapping.chat_id == chat_id,
                        TelegramChatMapping.is_active == True
                    ).first()
                    
                    if mapping:
                        user = db.query(User).filter(User.id == mapping.user_id).first()
                
                if user:
                    return {"username": user.username, "id": user.id}
                return None
            finally:
                db.close()

        try:
            user_data = await asyncio.to_thread(get_user_and_auto_link)
            
            if not user_data:
                if not bot_owner_id:
                    await self._send_raw(token, chat_id, "⚠️ *Account Not Linked*\n\nLink via Dashboard -> Settings")
                else:
                    logger.warning(f"User not found for update in {bot_owner_id} bot")
                return

            # 3. Forward to AI Analyst
            username = user_data["username"]
            logger.info(f"📨 Telegram (owner={bot_owner_id or 'System'}) from user={username} [thread={thread_id}]: {text[:50]}")
            
            # Generate JWT for the user
            access_token = create_access_token(data={"sub": username})
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                payload = {
                    "message": text,
                    "user_id": username,
                    "reply_via_telegram": True,
                    "telegram_chat_id": chat_id,
                    "telegram_message_id": message_id,
                    "telegram_thread_id": thread_id,  # Forward forum thread ID
                }
                resp = await client.post(
                    f"{self.ai_analyst_url}/api/v1/ai/chat/sessions/message",
                    headers=headers,
                    json=payload
                )
                if resp.status_code != 200:
                    logger.error(f"AI Analyst error: {resp.text[:100]}")
                    await self._send_raw(token, chat_id, "❌ AI service unavailable.")

        except Exception as e:
            logger.error(f"Failed to process update: {e}", exc_info=True)

    def _auto_link_chat(self, db: Session, user_id: UUID, chat_id: int):
        """Automatically create or update a mapping for personal bot users. Synchronous."""
        try:
            # 1. Check if the user already has a mapping (1:1 constraint)
            existing_user_mapping = db.query(TelegramChatMapping).filter(
                TelegramChatMapping.user_id == user_id
            ).first()
            
            if existing_user_mapping:
                if existing_user_mapping.chat_id != chat_id:
                    # User moved to a different chat, update it
                    old_chat = existing_user_mapping.chat_id
                    existing_user_mapping.chat_id = chat_id
                    existing_user_mapping.is_active = True
                    db.commit()
                    logger.info(f"Auto-updated Telegram link for user {user_id} from {old_chat} to {chat_id}")
                return

            # 2. Check if this chat_id is linked to SOMEONE ELSE (conflict)
            conflict = db.query(TelegramChatMapping).filter(
                TelegramChatMapping.chat_id == chat_id
            ).first()
            
            if conflict:
                # If it was linked to someone else on the SYSTEM bot, 
                # we can "reclaim" it for this user's personal bot context.
                conflict.user_id = user_id
            else:
                new_mapping = TelegramChatMapping(
                    user_id=user_id,
                    chat_id=chat_id,
                    is_active=True
                )
                db.add(new_mapping)
            db.commit()
        except Exception as e:
            logger.error(f"Auto-link failed: {e}")

    async def _send_raw(self, token: str, chat_id: int, text: str):
        url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
        except Exception:
            pass
