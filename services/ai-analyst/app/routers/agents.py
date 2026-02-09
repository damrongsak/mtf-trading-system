from fastapi import APIRouter, HTTPException, Header, Body
from typing import List, Dict, Any, Optional
import traceback
import logging
from datetime import datetime
from pydantic import BaseModel
import httpx
import os

from app.core.globals import services
from app.core.utils import extract_auth_token
from app.services.telegram import send_telegram_message

router = APIRouter(tags=["agents"])
logger = logging.getLogger(__name__)

# Agent Registry
AGENTS = {
    "market_observer": {
        "id": "market_observer",
        "name": "Market Observer",
        "role": "Analyst",
        "description": "Monitors market conditions and identifies trends across timeframes.",
        "status": "active",
        "capabilities": ["market_analysis", "trend_detection", "smc_recognition"]
    },
    "strategy_advisor": {
        "id": "strategy_advisor",
        "name": "Strategy Advisor",
        "role": "Advisor",
        "description": "Provides guidance on strategy parameters and optimization.",
        "status": "active",
        "capabilities": ["strategy_advice", "code_generation", "backtest_analysis"]
    },
    "daily_briefing": {
        "id": "daily_briefing",
        "name": "Daily Briefing",
        "role": "Reporter",
        "description": "Generates daily summary reports of market activity.",
        "status": "active",
        "capabilities": ["report_generation", "summarization"]
    }
}

# Request Models
class AgentRunRequest(BaseModel):
    input_text: str = "Generate a market situation report for XAU/USD."

class StrategyChatRequest(BaseModel):
    message: str
    user_id: str
    strategy_id: Optional[str] = None
    context_code: Optional[str] = None
    image_b64: Optional[str] = None
    reply_via_telegram: bool = False
    telegram_chat_id: Optional[int] = None
    telegram_message_id: Optional[int] = None  # For reply threading


# API Endpoints
@router.get("/agents", response_model=Dict[str, Any])
async def list_agents():
    """List all available AI agents."""
    return {
        "status": "success",
        "data": list(AGENTS.values())
    }


@router.get("/agents/{agent_id}", response_model=Dict[str, Any])
async def get_agent_details(agent_id: str):
    """Get details for a specific AI agent."""
    agent = AGENTS.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "status": "success",
        "data": agent
    }


@router.post("/agent/observer/run")
async def run_observer_agent(
    request: AgentRunRequest,
    authorization: str = Header(None, alias="Authorization")
):
    """Run the Market Observer agent."""
    if not services["market_observer"]:
        raise HTTPException(status_code=503, detail="AI Agent unavailable")
    
    try:
        report = await services["market_observer"].run(
            request.input_text,
            auth_header=authorization
        )
        return {
            "report": report,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error executing Market Observer: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/briefing")
async def run_daily_briefing(authorization: str = Header(None, alias="Authorization")):
    """Run the Daily Briefing agent."""
    if not services["daily_briefing"]:
        raise HTTPException(status_code=503, detail="Daily Briefing Agent unavailable")
    
    try:
        report = await services["daily_briefing"].run(
            "Generate valid Daily Briefing.",
            auth_header=authorization
        )
        return {
            "report": report,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error executing Daily Briefing: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/sessions/message")
async def chat_strategy(
    request: StrategyChatRequest,
    authorization: str = Header(None, alias="Authorization")
):
    """
    Chat with the Strategy Advisor Agent.
    Supports optional Telegram integration for bidirectional messaging.
    """
    if not services["strategy_advisor"]:
        raise HTTPException(
            status_code=503,
            detail="Strategy Advisor Agent unavailable (Check Gemini/Qdrant config)"
        )
    
    try:
        # Execute agent
        auth_token = extract_auth_token(authorization)
        result = await services["strategy_advisor"].run(
            input_text=request.message,
            user_id=request.user_id,
            auth_token=auth_token,
            context_code=request.context_code,
            image_b64=request.image_b64
        )
        
        # Send response to Telegram if requested
        if request.reply_via_telegram and request.telegram_chat_id:
            response_text = result.get("response", "No response generated.")
            await send_telegram_message(
                chat_id=request.telegram_chat_id,
                text=response_text,
                parse_mode="HTML",
                reply_to_message_id=request.telegram_message_id  # Thread the reply
            )
        
        return {
            "response": result.get("response"),
            "thoughts": result.get("thoughts"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in strategy chat: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent Error: {str(e)}")
