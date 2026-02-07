from fastapi import APIRouter, HTTPException, Header, Body
from typing import List, Dict, Any, Optional
import traceback
from datetime import datetime
from pydantic import BaseModel
from app.core.globals import services

router = APIRouter(
    tags=["agents"]
)

# ... (AGENTS dict remains same) ...
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

class AgentRunRequest(BaseModel):
    input_text: str = "Generate a market situation report for XAU/USD."

class StrategyChatRequest(BaseModel):
    message: str
    user_id: str
    strategy_id: Optional[str] = None
    context_code: Optional[str] = None
    image_b64: Optional[str] = None

@router.get("/agents", response_model=Dict[str, Any])
async def list_agents():
    """
    List all available AI agents.
    """
    return {
        "status": "success",
        "data": list(AGENTS.values())
    }

@router.get("/agents/{agent_id}", response_model=Dict[str, Any])
async def get_agent_details(agent_id: str):
    """
    Get details for a specific AI agent.
    """
    agent = AGENTS.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "status": "success",
        "data": agent
    }

@router.post("/agent/observer/run")
async def run_observer_agent(request: AgentRunRequest, authorization: str = Header(None, alias="Authorization")):
    if not services["market_observer"]:
        raise HTTPException(status_code=503, detail="AI Agent unavailable")
    
    try:
        report = await services["market_observer"].run(request.input_text, auth_header=authorization)
        return {"report": report, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        print(f"Error executing agent: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agent/briefing")
async def run_daily_briefing(authorization: str = Header(None, alias="Authorization")):
    if not services["daily_briefing"]:
        raise HTTPException(status_code=503, detail="Daily Briefing Agent unavailable")
    
    try:
        report = await services["daily_briefing"].run("Generate valid Daily Briefing.", auth_header=authorization)
        return {"report": report, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        print(f"Error executing agent: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/sessions/message")
async def chat_strategy(request: StrategyChatRequest, authorization: str = Header(None, alias="Authorization")):
    """
    Chat with the Strategy Advisor Agent regarding a specific strategy.
    """
    if not services["strategy_advisor"]:
        raise HTTPException(status_code=503, detail="Strategy Advisor Agent unavailable (Check Gemini/Qdrant config)")
    
    # Extract token
    auth_token = None
    if authorization and authorization.startswith("Bearer "):
        auth_token = authorization.split(" ")[1]

    try:
        result = await services["strategy_advisor"].run(
            input_text=request.message, 
            user_id=request.user_id,
            auth_token=auth_token, # Pass the extracted token
            context_code=request.context_code,
            image_b64=request.image_b64
        )
        return {
            "response": result.get("response"),
            "thoughts": result.get("thoughts"),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        print(f"Error in strategy chat: {str(e)}")
        traceback.print_exc()
        # Fallback error response properly formatted
        raise HTTPException(status_code=500, detail=f"Agent Error: {str(e)}")
