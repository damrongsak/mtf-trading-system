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
from app.utils.response import success_response

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
    thread_id: Optional[str] = None # For LangGraph persistence


@router.get("/diagnose")
async def run_system_diagnostics(
    authorization: str = Header(None, alias="Authorization")
):
    """Run system-wide diagnostic smoke tests for all tools."""
    from app.core.bootstrap import run_diagnostics
    
    try:
        auth_token = extract_auth_token(authorization)
        results = await run_diagnostics(auth_token=auth_token)
        
        # Calculate overall health
        success_count = sum(1 for r in results if r["status"] == "SUCCESS")
        overall_status = "HEALTHY" if success_count == len(results) else "DEGRADED"
        
        return success_response(
            data={
                "status": overall_status,
                "tool_health": results,
                "summary": f"{success_count}/{len(results)} tools passed."
            },
            message="System diagnostics completed"
        )
    except Exception as e:
        logger.error(f"Diagnostic failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# API Endpoints
@router.get("/agents", response_model=Dict[str, Any])
async def list_agents():
    """List all available AI agents."""
    return success_response(data=list(AGENTS.values()))


@router.get("/agents/{agent_id}", response_model=Dict[str, Any])
async def get_agent_details(agent_id: str):
    """Get details for a specific AI agent."""
    agent = AGENTS.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return success_response(data=agent)


@router.post("/agent/observer/run")
async def run_observer_agent(
    request: AgentRunRequest,
    authorization: str = Header(None, alias="Authorization")
):
    """Run the Market Observer (via Strategy Advisor)."""
    if not services["strategy_advisor"]:
        raise HTTPException(status_code=503, detail="AI Agent unavailable")
    
    try:
        auth_token = extract_auth_token(authorization)
        result = await services["strategy_advisor"].run(
            input_text=request.input_text,
            user_id="observer_report",
            auth_token=auth_token
        )
        return success_response(
            data=result,
            message="Observer agent execution successful"
        )
    except Exception as e:
        logger.error(f"Error executing Market Observer flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/briefing")
async def run_daily_briefing(authorization: str = Header(None, alias="Authorization")):
    """Run the Daily Briefing (via Strategy Advisor)."""
    if not services["strategy_advisor"]:
        raise HTTPException(status_code=503, detail="Strategy Advisor unavailable")
    
    try:
        auth_token = extract_auth_token(authorization)
        result = await services["strategy_advisor"].run(
            input_text="Generate my Daily Briefing.",
            user_id="briefing_user", # User context is handled via auth_token in nodes
            auth_token=auth_token
        )
        return success_response(
            data=result,
            message="Daily briefing execution successful"
        )
    except Exception as e:
        logger.error(f"Error executing Daily Briefing flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/sessions/stream")
async def chat_strategy_stream(
    request: StrategyChatRequest,
    authorization: str = Header(None, alias="Authorization")
):
    """
    Streaming chat with Strategy Advisor Agent.
    """
    if not services["strategy_advisor"]:
        raise HTTPException(status_code=503, detail="Strategy Advisor unavailable")
    
    from fastapi.responses import StreamingResponse
    import json

    async def event_generator():
        auth_token = extract_auth_token(authorization)
        try:
            async for event in services["strategy_advisor"].stream(
                input_text=request.message,
                user_id=request.user_id,
                auth_token=auth_token,
                context_code=request.context_code,
                image_b64=request.image_b64,
                thread_id=request.thread_id
            ):
                yield json.dumps(event) + "\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield json.dumps({"type": "error", "content": str(e)}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


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
            image_b64=request.image_b64,
            thread_id=request.thread_id
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
        
        return success_response(
            data=result,
            message="Message processed by Strategy Advisor"
        )
        
    except Exception as e:
        logger.error(f"Error in strategy chat: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent Error: {str(e)}")
