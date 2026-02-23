from fastapi import APIRouter, HTTPException, Depends, Header, Request
from typing import Optional, List, Dict, Any
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timezone
import httpx
import os
import logging
import uuid
import pydantic

logger = logging.getLogger(__name__)

# Standard app imports
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.chat import ChatSession, ChatMessage
from app.models.user import User
from app.security import get_current_user
from app.schemas.ai import MarketAnalysisRequest, JournalAnalysisRequest, AnalysisResponse
from app.schemas.response import APIResponse
from app.utils.response import success_response
from app.utils.cache import cached_response

# Generated schemas
from app.schemas.generated import (
    APIResponseChatSessionList, 
    APIResponseChatMessageList,
    APIResponseChatSession,
    APIResponseChatMessage,
    APIResponseAIReport,
    ChatSessionCreate, 
    ChatMessageCreate, 
    ChatSession as ChatSessionSchema, 
    ChatMessage as ChatMessageSchema,
    ResponseStatus
)

router = APIRouter(
    prefix="/api/v1/ai",
    tags=["ai"]
)

AI_SERVICE_URL = os.getenv("AI_ANALYST_URL", "http://ai-analyst:8000")

@router.get("/agents")
async def list_agents(request: Request):
    """
    Proxy list agents request to AI Analyst service.
    """
    request_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": request_id} if request_id else {}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{AI_SERVICE_URL}/api/v1/ai/agents",
                headers=headers,
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            logger.error(f"AI service connection failed to {AI_SERVICE_URL}: {exc}")
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            logger.error(f"AI service error {exc.response.status_code}: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"AI service error: {exc.response.text}")

@router.post("/market-analysis", response_model=APIResponse[AnalysisResponse])
async def analyze_market(req: MarketAnalysisRequest, request: Request):
    """
    Proxy market analysis request to AI Analyst service.
    """
    request_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": request_id} if request_id else {}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{AI_SERVICE_URL}/api/v1/analyze/market", 
                json=req.model_dump(mode='json'),
                headers=headers,
                timeout=30.0 # LLMs can be slow
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            logger.error(f"AI service connection failed to {AI_SERVICE_URL}: {exc}")
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            logger.error(f"AI service error {exc.response.status_code}: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"AI service error: {exc.response.text}")

@router.post("/journal-analysis", response_model=APIResponse[AnalysisResponse])
async def analyze_journal(req: JournalAnalysisRequest, request: Request):
    """
    Proxy journal analysis request to AI Analyst service.
    """
    request_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": request_id} if request_id else {}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{AI_SERVICE_URL}/api/v1/analyze/journal", 
                json=req.model_dump(mode='json'),
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            logger.error(f"AI service connection failed to {AI_SERVICE_URL}: {exc}")
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            logger.error(f"AI service error {exc.response.status_code}: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"AI service error: {exc.response.text}")

class AgentRunRequest(pydantic.BaseModel):
    input_text: str

@router.post("/agent/observer/run")
async def run_market_observer(
    req: AgentRunRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="token"))
):
    """
    Proxy agent run request to AI Analyst service with authentication.
    """
    request_id = getattr(request.state, "request_id", None)
    headers = {"Authorization": f"Bearer {token}"}
    if request_id:
        headers["X-Request-ID"] = request_id
        
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{AI_SERVICE_URL}/api/v1/ai/agent/observer/run", 
                json=req.model_dump(),
                headers=headers,
                timeout=120.0 # Agents can be slow
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            logger.error(f"AI service connection failed to {AI_SERVICE_URL}: {exc}")
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            logger.error(f"AI service error {exc.response.status_code}: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"AI service error: {exc.response.text}")

@router.get("/briefing")
@cached_response(ttl=3600)
async def get_daily_briefing(
    request: Request,
    current_user: User = Depends(get_current_user),
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="token"))
):
    """
    Get the latest daily briefing from AI Analyst.
    """
    async with httpx.AsyncClient() as client:
        try:
            # We call the POST endpoint on AI Analyst to generate/fetch
            request_id = getattr(request.state, "request_id", None)
            headers = {"Authorization": f"Bearer {token}"}
            if request_id:
                headers["X-Request-ID"] = request_id

            response = await client.post(
                f"{AI_SERVICE_URL}/api/v1/ai/agent/briefing",
                headers=headers,
                timeout=120.0 
            )
            response.raise_for_status()
            resp_data = response.json()
            
            # Extract data from AI Analyst's APIResponse wrapper
            inner_data = resp_data.get("data", {})
            if not inner_data and resp_data.get("status") == "error":
                logger.error(f"AI Analyst returned error: {resp_data.get('message')}")
                raise HTTPException(status_code=500, detail=resp_data.get("message"))

            # Transform to Dashboard Briefing format
            # AI Analyst run() returns {"response": "...", "thoughts": "..."}
            return success_response(data={
                "content": inner_data.get("response") or inner_data.get("report") or "",
                "generated_at": inner_data.get("timestamp") or datetime.now(timezone.utc).isoformat(),
                "type": "DAILY"
            })
        except httpx.RequestError as exc:
            logger.error(f"AI service connection failed: {exc}")
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            logger.error(f"AI service returned {exc.response.status_code}: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"AI service error: {exc.response.text}")

class StrategyChatRequest(pydantic.BaseModel):
    message: str
    user_id: str
    strategy_id: Optional[str] = None
    context_code: Optional[str] = None
    image_b64: Optional[str] = None
    reply_via_telegram: bool = False
    telegram_chat_id: Optional[int] = None
    telegram_message_id: Optional[int] = None
    thread_id: Optional[str] = None

@router.post("/chat/sessions/message")
async def chat_strategy(
    request: Request,
    chat_req: StrategyChatRequest, 
    authorization: str = Header(None, alias="Authorization")
):
    """
    Direct chat with Strategy Advisor (Stateless wrapper for CLI/Quick Chat).
    Proxies to AI Analyst service.
    """
    request_id = getattr(request.state, "request_id", None)
    headers = {"Authorization": authorization} if authorization else {}
    if request_id:
        headers["X-Request-ID"] = request_id

    async with httpx.AsyncClient() as client:
        try:
            # Forward to AI Analyst
            response = await client.post(
                f"{AI_SERVICE_URL}/api/v1/ai/chat/sessions/message", 
                json=chat_req.model_dump(),
                headers=headers,
                timeout=180.0 # Very Long timeout for CoT
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            logger.error(f"AI Service Connection Failed: {exc} | URL: {AI_SERVICE_URL}")
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {type(exc).__name__} - {exc}")
        except httpx.HTTPStatusError as exc:
            logger.error(f"AI Service Error {exc.response.status_code}: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"AI service error: {exc.response.text}")

@router.get("/chat/sessions", response_model=APIResponseChatSessionList)
def list_chat_sessions(
    strategy_id: uuid.UUID = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ChatSession).filter(ChatSession.user_id == current_user.id)
    if strategy_id:
        query = query.filter(ChatSession.strategy_id == strategy_id)
    
    sessions = query.order_by(ChatSession.updated_at.desc()).all()
    
    return {
        "status": "success",
        "data": sessions
    }

@router.post("/chat/sessions", response_model=APIResponseChatSession)
def create_chat_session(
    session_in: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_session = ChatSession(
        user_id=current_user.id,
        strategy_id=session_in.strategy_id,
        title=session_in.initial_message[:50] + "..." if session_in.initial_message else "New Chat",
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return {
        "status": "success",
        "data": new_session
    }

@router.get("/chat/sessions/{session_id}/messages", response_model=APIResponseChatMessageList)
def list_session_messages(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.asc()).all()
    
    return {
        "status": "success",
        "data": messages
    }

@router.post("/chat/sessions/{session_id}/messages", response_model=APIResponseChatMessage)
async def send_chat_message(
    session_id: uuid.UUID,
    msg_in: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    authorization: str = Header(None, alias="Authorization")
):
    # 1. Validate Session
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 2. Save User Message
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=msg_in.content,
        context_snapshot=msg_in.context_snapshot
    )
    db.add(user_msg)
    
    # Update session timestamp
    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user_msg)
    
    # 3. Call AI Service
    ai_response_text = ""
    try:
        # Prepare payload for AI Analyst
        # We need to pass the code context if it exists in snapshot
        context_code = None
        image_b64 = None
        if msg_in.context_snapshot:
             if "code" in msg_in.context_snapshot:
                 context_code = msg_in.context_snapshot["code"]
             if "image_b64" in msg_in.context_snapshot:
                 image_b64 = msg_in.context_snapshot["image_b64"]
             
        payload = {
            "message": msg_in.content,
            "user_id": str(current_user.id),
            "strategy_id": str(session.strategy_id) if session.strategy_id else None,
            "context_code": context_code,
            "image_b64": image_b64,
            "thread_id": str(session_id) # Use session_id as LangGraph thread_id
        }
        
        async with httpx.AsyncClient() as client:
            # Pass the Authorization header from the incoming request if it exists
            request_id = getattr(request.state, "request_id", None)
            headers = {}
            if authorization:
                headers["Authorization"] = authorization
            if request_id:
                headers["X-Request-ID"] = request_id
                
            resp = await client.post(
                f"{AI_SERVICE_URL}/api/v1/ai/chat/sessions/message",
                json=payload,
                headers=headers,
                timeout=180.0 # Very Long timeout for CoT and Multi-Step Reasoning
            )
            
            if resp.status_code == 200:
                data = resp.json()
                # AI Analyst returns success_response with data={response: ...}
                ai_response_text = data.get("data", {}).get("response", "")
            else:
                ai_response_text = f"Error from AI Agent: {resp.text}"
                
    except Exception as e:
        logger.error(f"AI Service Call Failed: {e}")
        ai_response_text = "I'm sorry, I'm currently unable to connect to the AI brain. Please try again later."
    
    # 4. Save AI Response
    ai_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=ai_response_text
    )
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)
    
    return {
        "status": "success",
        "data": ai_msg
    }
