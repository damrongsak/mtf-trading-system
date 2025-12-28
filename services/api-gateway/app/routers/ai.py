from fastapi import APIRouter, HTTPException
from app.schemas.ai import MarketAnalysisRequest, JournalAnalysisRequest, AnalysisResponse
from app.schemas.response import APIResponse
from app.utils.response import success_response
import httpx
import os

router = APIRouter(
    prefix="/api/v1/ai",
    tags=["ai"]
)

AI_SERVICE_URL = os.getenv("AI_ANALYST_URL", "http://ai-analyst:8000")

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
async def run_market_observer(req: AgentRunRequest):
    """
    Proxy agent run request to AI Analyst service.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{AI_SERVICE_URL}/agent/observer/run", 
                json=req.model_dump(),
                timeout=60.0 # Agents can be slow
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"AI service error: {exc.response.text}")

# --- AI Chat Integration ---
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models.chat import ChatSession, ChatMessage
from app.models.user_fund import User
from app.core.security import get_current_user
from fastapi import Depends
from app.schemas.generated import (
    APIResponse_ChatSessionList, 
    APIResponse_ChatSession,
    APIResponse_ChatMessageList,
    APIResponse_ChatMessage,
    ChatSessionCreate,
    ChatMessageCreate
)
from datetime import datetime
import uuid

@router.get("/chat/sessions", response_model=APIResponse_ChatSessionList)
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

@router.post("/chat/sessions", response_model=APIResponse_ChatSession)
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

@router.get("/chat/sessions/{session_id}/messages", response_model=APIResponse_ChatMessageList)
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

@router.post("/chat/sessions/{session_id}/messages", response_model=APIResponse_ChatMessage)
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
    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user_msg)
    
    # 3. Call AI Service
    ai_response_text = ""
    try:
        # Prepare payload for AI Analyst
        # We need to pass the code context if it exists in snapshot
        context_code = None
        if msg_in.context_snapshot and "code" in msg_in.context_snapshot:
             context_code = msg_in.context_snapshot["code"]
             
        payload = {
            "message": msg_in.content,
            "user_id": str(current_user.id),
            "strategy_id": str(session.strategy_id) if session.strategy_id else None,
            "context_code": context_code
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
