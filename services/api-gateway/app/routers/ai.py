from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from app.schemas.ai import MarketAnalysisRequest, JournalAnalysisRequest, AnalysisResponse
from app.schemas.response import APIResponse
from app.utils.response import success_response
import httpx
import os

from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.chat import ChatSession, ChatMessage
from app.models.user import User
from app.security import get_current_user

router = APIRouter(
    prefix="/api/v1/ai",
    tags=["ai"]
)

AI_SERVICE_URL = os.getenv("AI_ANALYST_URL", "http://ai-analyst:8000")

@router.get("/agents")
async def list_agents():
    """
    Proxy list agents request to AI Analyst service.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{AI_SERVICE_URL}/api/v1/ai/agents",
                timeout=5.0
            )
            response.raise_for_status()
            # Wrap in APIResponse structure if not already
            return success_response(data=response.json().get("data", []))
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"AI service error: {exc.response.text}")

@router.post("/market-analysis", response_model=APIResponse[AnalysisResponse])
async def analyze_market(req: MarketAnalysisRequest):
    """
    Proxy market analysis request to AI Analyst service.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{AI_SERVICE_URL}/analyze/market", 
                json=req.model_dump(mode='json'),
                timeout=30.0 # LLMs can be slow
            )
            response.raise_for_status()
            return success_response(data=response.json())
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"AI service error: {exc.response.text}")

@router.post("/journal-analysis", response_model=APIResponse[AnalysisResponse])
async def analyze_journal(req: JournalAnalysisRequest):
    """
    Proxy journal analysis request to AI Analyst service.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{AI_SERVICE_URL}/analyze/journal", 
                json=req.model_dump(mode='json'),
                timeout=30.0
            )
            response.raise_for_status()
            return success_response(data=response.json())
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"AI service error: {exc.response.text}")

from pydantic import BaseModel
class AgentRunRequest(BaseModel):
    input_text: str

@router.post("/agent/observer/run")
async def run_market_observer(
    req: AgentRunRequest,
    current_user: User = Depends(get_current_user),
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="token"))
):
    """
    Proxy agent run request to AI Analyst service with authentication.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{AI_SERVICE_URL}/agent/observer/run", 
                json=req.model_dump(),
                headers={"Authorization": f"Bearer {token}"},
                timeout=60.0 # Agents can be slow
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"AI service error: {exc.response.text}")

@router.get("/briefing")
async def get_daily_briefing(
    current_user: User = Depends(get_current_user),
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="token"))
):
    """
    Get the latest daily briefing from AI Analyst.
    """
    async with httpx.AsyncClient() as client:
        try:
            # We call the POST endpoint on AI Analyst to generate/fetch
            response = await client.post(
                f"{AI_SERVICE_URL}/agent/briefing",
                headers={"Authorization": f"Bearer {token}"},
                timeout=60.0 
            )
            response.raise_for_status()
            data = response.json()
            
            # Transform to Briefing model format
            return success_response(data={
                "content": data.get("report", ""),
                "generated_at": data.get("timestamp"),
                "type": "DAILY"
            })
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"AI service error: {exc.response.text}")

# --- AI Chat Integration ---

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
from datetime import datetime, timezone
import uuid

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
    db: Session = Depends(get_db)
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
            "image_b64": image_b64
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{AI_SERVICE_URL}/chat/strategy",
                json=payload,
                timeout=60.0 # Long timeout for CoT
            )
            
            if resp.status_code == 200:
                data = resp.json()
                ai_response_text = data.get("response", "")
            else:
                ai_response_text = f"Error from AI Agent: {resp.text}"
                
    except Exception as e:
        print(f"AI Service Call Failed: {e}")
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
