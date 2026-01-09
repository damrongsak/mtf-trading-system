from fastapi import APIRouter, HTTPException

from app.agents.market_observer import MarketObserverAgent
from app.agents.strategy_advisor import StrategyAdvisorAgent
from app.agents.daily_briefing import DailyBriefingAgent
from typing import List, Dict, Any

router = APIRouter(
    prefix="/agents",
    tags=["agents"]
)

# In-memory registry (should be replaced by DB or Agent Registry service later)
# For now, we manually list the known agents in this service
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

@router.get("", response_model=Dict[str, Any])
async def list_agents():
    """
    List all available AI agents.
    """
    return {
        "status": "success",
        "data": list(AGENTS.values())
    }

@router.get("/{agent_id}", response_model=Dict[str, Any])
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
