from fastapi import APIRouter, HTTPException, Depends, Header, Request, Body, Query
from typing import Optional, List, Dict, Any, Tuple
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timezone
import httpx
import os
import logging
import uuid
import pydantic

logger = logging.getLogger(__name__)

# Standard app imports
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.chat import ChatSession, ChatMessage
from app.models.user import User
from app.security import get_current_user
from app.schemas.response import APIResponse
from app.utils.response import success_response
from app.utils.cache import cached_response

def session_to_dict(s):
    return {
        "id": s.id, "user_id": s.user_id, "strategy_id": s.strategy_id,
        "title": s.title, "created_at": s.created_at, "updated_at": s.updated_at
    }

def msg_to_dict(m):
    return {
        "id": m.id, "session_id": m.session_id, "role": m.role,
        "content": m.content, "context_snapshot": m.context_snapshot,
        "created_at": m.created_at
    }

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
    ResponseStatus,
    AIJobAccepted,
    AIJobStatus
)
import json
from app.utils.redis_client import get_redis_client

from app.utils.http_client import get_internal_client

router = APIRouter(
    prefix="/api/v1/ai",
    tags=["ai"]
)

AI_SERVICE_URL = os.getenv("AI_ANALYST_URL", "http://ai-analyst:8000")
AI_SERVICE_TIMEOUT = float(os.getenv("AI_SERVICE_TIMEOUT", "600.0")) # Increased for indicator heavy reasoning

async def _get_broker_account_info(db: Session, user_id: Any) -> Tuple[Optional[str], Optional[str]]:
    """Helper to get user's active broker account ID and fund ID."""
    from app.models.broker_account import BrokerAccount
    from app.models.user_fund import UserFund, Fund
    
    account = db.query(BrokerAccount).join(Fund).join(UserFund).filter(
        UserFund.user_id == user_id,
        BrokerAccount.is_active == True
    ).first()
    
    if not account:
        logger.warning(f"No active BrokerAccount found for user_id: {user_id}")
        return None, None
    else:
        logger.info(f"Retrieved active Account ID: {account.id}, Fund ID: {account.fund_id} for user_id: {user_id}")
        return str(account.id), str(account.fund_id)

@router.get("/agents")
async def list_agents(request: Request):
    """
    Proxy list agents request to AI Analyst service.
    """
    request_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": request_id} if request_id else {}
    
    async with await get_internal_client() as client:
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

@router.get("/diagnose")
async def proxy_diagnose(
    request: Request,
    authorization: str = Header(None, alias="Authorization")
):
    """Proxy diagnose smoke tests to AI Analyst."""
    request_id = getattr(request.state, "request_id", None)
    headers = {"Authorization": authorization} if authorization else {}
    if request_id:
        headers["X-Request-ID"] = request_id
        
    async with await get_internal_client() as client:
        try:
            logger.info(f"Proxying diagnose to {AI_SERVICE_URL}/api/v1/ai/diagnose with headers: {headers}")
            response = await client.get(
                f"{AI_SERVICE_URL}/api/v1/ai/diagnose",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            err_type = type(e).__name__
            err_msg = str(e)
            logger.error(f"!!! DIAGNOSE PROXY CRITICAL FAILURE !!! Type: {err_type} | Message: {err_msg}")
            raise HTTPException(status_code=500, detail=f"Proxy Error: {err_type} - {err_msg}")

@router.post("/agent/memory/sync")
async def proxy_memory_sync(
    request: Request,
    authorization: str = Header(None, alias="Authorization")
):
    """Proxy episodic memory sync to AI Analyst."""
    request_id = getattr(request.state, "request_id", None)
    headers = {"Authorization": authorization} if authorization else {}
    if request_id:
        headers["X-Request-ID"] = request_id
        
    async with await get_internal_client() as client:
        try:
            response = await client.post(
                f"{AI_SERVICE_URL}/api/v1/ai/agent/memory/sync",
                headers=headers,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Memory sync proxy failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/briefing")
# @cached_response(ttl=3600)
async def get_daily_briefing(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="token"))
):
    """
    Get the latest daily briefing from AI Analyst.
    """
    async with await get_internal_client() as client:
        try:
            request_id = getattr(request.state, "request_id", None)
            account_id = await _get_broker_account_id(db, current_user.id)
            
            logger.error(f"DEBUG_TRACER: Gateway proxying briefing for user {current_user.id}, account {account_id}")
            headers = {"Authorization": f"Bearer {token}"}
            if request_id:
                headers["X-Request-ID"] = request_id
            if account_id:
                headers["X-Broker-Account-ID"] = account_id

            response = await client.post(
                f"{AI_SERVICE_URL}/api/v1/ai/agent/briefing",
                headers=headers,
                timeout=AI_SERVICE_TIMEOUT 
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="token"))
):
    """
    Direct chat with Strategy Advisor (Stateless wrapper for CLI/Quick Chat).
    Proxies to AI Analyst service. Injects authenticated user/fund context.
    """
    request_id = getattr(request.state, "request_id", None)
    headers = {"Authorization": f"Bearer {token}"}
    if request_id:
        headers["X-Request-ID"] = request_id

    # Resolve active fund for this user to enable indicator data isolation
    from app.models.user_fund import UserFund
    user_fund = db.query(UserFund).filter(UserFund.user_id == current_user.id).first()
    active_fund_id = str(user_fund.fund_id) if user_fund else None

    # Override with authenticated context — never trust caller-supplied user_id
    payload = chat_req.model_dump()
    payload["user_id"] = str(current_user.id)
    payload["active_fund_id"] = active_fund_id

    async with await get_internal_client() as client:
        try:
            # Forward to AI Analyst with enriched context
            response = await client.post(
                f"{AI_SERVICE_URL}/api/v1/ai/chat/sessions/message", 
                json=payload,
                headers=headers,
                timeout=AI_SERVICE_TIMEOUT # Long timeout for CoT
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            logger.error(f"AI Service Connection Failed: {exc} | URL: {AI_SERVICE_URL}")
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {type(exc).__name__} - {exc}")
        except httpx.HTTPStatusError as exc:
            logger.error(f"AI Service Error {exc.response.status_code}: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"AI service error: {exc.response.text}")

@router.post("/chat/sessions/stream")
async def chat_strategy_stream(
    request: Request,
    chat_req: StrategyChatRequest, 
    authorization: str = Header(None, alias="Authorization")
):
    """
    Streaming proxy for Strategy Advisor.
    """
    request_id = getattr(request.state, "request_id", None)
    headers = {"Authorization": authorization, "Accept": "application/x-ndjson"} if authorization else {"Accept": "application/x-ndjson"}
    if request_id:
        headers["X-Request-ID"] = request_id

    from fastapi.responses import StreamingResponse

    async def stream_proxy():
        async with await get_internal_client() as client:
            async with client.stream(
                "POST",
                f"{AI_SERVICE_URL}/api/v1/ai/chat/sessions/stream",
                json=chat_req.model_dump(),
                headers=headers,
                timeout=AI_SERVICE_TIMEOUT
            ) as response:
                # Check for errors before streaming
                if response.status_code >= 400:
                    await response.aread()
                    yield json.dumps({"type": "error", "content": f"AI Service Error {response.status_code}: {response.text}"}) + "\n"
                    return

                try:
                    async for chunk in response.aiter_lines():
                        if chunk:
                            yield chunk + "\n"
                except (httpx.ReadError, httpx.RemoteProtocolError) as e:
                    logger.error(f"Streaming connection lost: {e}")
                    yield json.dumps({"type": "error", "content": "Peer closed connection prematurely. Technical details: " + str(e)}) + "\n"

    return StreamingResponse(stream_proxy(), media_type="application/x-ndjson")


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
    
    return success_response(data=[session_to_dict(s) for s in sessions])

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
    
    return success_response(data=session_to_dict(new_session))

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
    
    return success_response(data=[msg_to_dict(m) for m in messages])

@router.post("/chat/sessions/{session_id}/messages", response_model=APIResponseChatMessage)
async def send_chat_message(
    session_id: uuid.UUID,
    msg_in: ChatMessageCreate,
    request: Request, # Added to support request_id extraction
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
        
        async with await get_internal_client() as client:
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
                timeout=AI_SERVICE_TIMEOUT # Long timeout for CoT and Multi-Step Reasoning
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
    
    return success_response(data=msg_to_dict(ai_msg))

@router.post("/ingest/upload")
async def proxy_upload_file(request: Request):
    """Proxy file upload to AI Analyst."""
    async with await get_internal_client() as client:
        # We need to forward the multipart content
        content_type = request.headers.get("Content-Type")
        body = await request.body()
        
        response = await client.post(
            f"{AI_SERVICE_URL}/api/v1/ai/ingest/upload",
            content=body,
            headers={"Content-Type": content_type},
            timeout=AI_SERVICE_TIMEOUT
        )
        return response.json()

@router.post("/library/ingest")
async def proxy_library_ingest(request: Request):
    """Proxy library book ingestion to AI Analyst."""
    async with await get_internal_client() as client:
        content_type = request.headers.get("Content-Type")
        body = await request.body()
        
        response = await client.post(
            f"{AI_SERVICE_URL}/api/v1/ai/library/ingest",
            content=body,
            headers={"Content-Type": content_type},
            timeout=AI_SERVICE_TIMEOUT
        )
        return response.json()

@router.get("/library/status/{filename}")
async def proxy_library_status(filename: str):
    """Proxy library book ingestion status to AI Analyst."""
    async with await get_internal_client() as client:
        response = await client.get(
            f"{AI_SERVICE_URL}/api/v1/ai/library/status/{filename}",
            timeout=10.0
        )
        return response.json()

@router.get("/library/list")
async def proxy_library_list():
    """Proxy library book list to AI Analyst."""
    async with await get_internal_client() as client:
        response = await client.get(
            f"{AI_SERVICE_URL}/api/v1/ai/library/list",
            timeout=10.0
        )
        return response.json()

@router.get("/admin/qdrant/health")
async def proxy_qdrant_health(request: Request):
    """Proxy Qdrant health check to AI Analyst."""
    async with await get_internal_client() as client:
        response = await client.get(
            f"{AI_SERVICE_URL}/api/v1/ai/admin/qdrant/health",
            timeout=10.0
        )
        return response.json()

@router.post("/admin/qdrant/collections/{collection_name}/clear")
async def proxy_clear_qdrant_collection(collection_name: str):
    """Proxy Qdrant collection clear to AI Analyst."""
    async with await get_internal_client() as client:
        response = await client.post(
            f"{AI_SERVICE_URL}/api/v1/ai/admin/qdrant/collections/{collection_name}/clear",
            timeout=30.0
        )
        return response.json()







@router.post("/think", status_code=202)
async def proxy_ai_think(
    request: Request,
    payload: Dict[str, Any] = Body(...),
    authorization: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Unified AI Thinking request - Pushed to async message queue.
    """
    request_id = getattr(request.state, "request_id", None)
    headers = {"Authorization": authorization} if authorization else {}
    if request_id:
        headers["X-Request-ID"] = request_id
    
    account_id, fund_id = await _get_broker_account_info(db, current_user.id)
    if account_id:
        headers["X-Broker-Account-ID"] = account_id
    if fund_id:
        headers["X-Fund-ID"] = fund_id

    job_id = str(uuid.uuid4())
    redis = await get_redis_client()
    
    # Store initial status
    await redis.set(
        f"ai:think:result:{job_id}", 
        json.dumps({"status": "processing"}),
        ex=86400  # 24 hour TTL
    )
    
    # Push to worker stream
    cmd_payload = {
        "job_id": job_id,
        "payload": json.dumps(payload),
        "headers": json.dumps(headers)
    }
    
    await redis.xadd("ai:think:cmd", cmd_payload, maxlen=1000)
    logger.info(f"Pushed AI job {job_id} to stream ai:think:cmd")
    
    return {"job_id": job_id, "status": "processing"}

@router.get("/jobs/{job_id}")
async def get_ai_job_status(job_id: str):
    """
    Poll API for AI Analyst results.
    """
    redis = await get_redis_client()
    result_str = await redis.get(f"ai:think:result:{job_id}")
    
    if not result_str:
        raise HTTPException(status_code=404, detail="Job not found or expired")
        
    result_data = json.loads(result_str)
    return result_data


@router.get("/knowledge/context")
async def proxy_knowledge_context(
    request: Request,
    symbol: str = Query(..., description="The symbol to query semantic context for"),
    include_score: bool = Query(True, description="Whether to include knowledge-driven multiplier"),
    authorization: str = Header(None, alias="Authorization")
):
    """
    Proxy Knowledge Context request to AI Analyst service.
    """
    request_id = getattr(request.state, "request_id", None)
    headers = {"Authorization": authorization} if authorization else {}
    if request_id:
        headers["X-Request-ID"] = request_id

    async with await get_internal_client() as client:
        try:
            response = await client.get(
                f"{AI_SERVICE_URL}/api/v1/ai/knowledge/context",
                params={"symbol": symbol, "include_score": str(include_score).lower()},
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

@router.post("/mri/coaching")
async def proxy_mri_coaching(
    request: Request,
    payload: Dict[str, Any] = Body(...),
    authorization: str = Header(None, alias="Authorization")
):
    """
    Proxy MRI Coaching request to AI Analyst service.
    """
    request_id = getattr(request.state, "request_id", None)
    headers = {"Authorization": authorization} if authorization else {}
    if request_id:
        headers["X-Request-ID"] = request_id

    async with await get_internal_client() as client:
        try:
            response = await client.post(
                f"{AI_SERVICE_URL}/api/v1/ai/mri/coaching",
                json=payload,
                headers=headers,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            logger.error(f"AI service connection failed to {AI_SERVICE_URL}: {exc}")
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            logger.error(f"AI service error {exc.response.status_code}: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"AI service error: {exc.response.text}")
