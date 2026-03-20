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
from app.services.guardrail import check_guardrails
from app.agents.universal import UniversalAgent
from app.schemas.agent import AgentConfig
from app.schemas.orchestration import AIThinkRequest, AIThinkResponse, Severity

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
    },
    "journal_analyst": {
        "id": "journal_analyst",
        "name": "Journal Analyst",
        "role": "Reviewer",
        "description": "Reviews closed trades to extract lessons and psychological patterns.",
        "status": "active",
        "capabilities": ["trade_post_mortem", "episodic_memory", "pattern_recognition"]
    },
    "portfolio_manager": {
        "id": "portfolio_manager",
        "name": "Portfolio Manager",
        "role": "Risk Manager",
        "description": "Management of open positions (BE moves, trailing stops, risk parity).",
        "status": "active",
        "capabilities": ["trade_management", "risk_mitigation", "dynamic_sl_tp"]
    },
    "entry_reason": {
        "id": "entry_reason",
        "name": "Entry Reason",
        "role": "Reviewer",
        "description": "Analyzes the technical and emotional rationale behind a trade entry.",
        "status": "active",
        "capabilities": ["reason_learning", "conviction_assessment"]
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
    telegram_thread_id: Optional[int] = None   # For forum topics
    thread_id: Optional[str] = None # For LangGraph persistence


class UniversalAgentRunRequest(BaseModel):
    config: AgentConfig
    input_text: str
    user_id: str = "default_user"


class SkillCreatorRunRequest(BaseModel):
    user_intent: str
    user_id: str = "skill_creator"


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


@router.post("/think", response_model=Dict[str, Any])
async def ai_think(
    request: AIThinkRequest,
    authorization: str = Header(None, alias="Authorization")
):
    """
    Unified AI Orchestrator Entry Point.
    Routes requests to StrategyAdvisor, MarketObserver, or General based on intent and market regime.
    """
    # 1. Check for Strategy Advisor (Main Orchestrator)
    if not services.get("strategy_advisor"):
        raise HTTPException(status_code=503, detail="AI Orchestrator unavailable")
    
    try:
        # 2. Check Guardrails
        guardrail_result = check_guardrails(request.message)
        if guardrail_result.blocked:
            return success_response(
                data={
                    "response": f"⚠️ Request blocked: {guardrail_result.reason}",
                    "severity": Severity.ROUTINE,
                    "metadata": {"guardrail_triggered": True}
                },
                message="Request blocked by guardrail"
            )

        # 3. Execute Unified Thinking (via Strategy Advisor which acts as the main graph)
        # Note: In a true Supervisor pattern, we might call services["supervisor"].
        # But our StrategyAdvisor IS the complex graph that starts with a supervisor/router node.
        auth_token = extract_auth_token(authorization)
        
        result = await services["strategy_advisor"].run(
            input_text=request.message,
            user_id="unified_user",
            auth_token=auth_token,
            image_b64=request.image_b64,
            thread_id=request.thread_id,
            # Pass hint if provided
            intent_hint=request.intent
        )
        
        # 4. Format Response according to AIThinkResponse
        return success_response(
            data={
                "response": result.get("response", "No response generated"),
                "intent_resolved": result.get("intent", "general"),
                "severity": result.get("market_severity", Severity.ROUTINE),
                "metadata": result.get("metadata", {}),
                "timestamp": datetime.now()
            },
            message="AI Thought processed successfully"
        )

    except Exception as e:
        logger.error(f"Unified AI Error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Orchestration Error: {str(e)}")



@router.post("/agent/observer/run", tags=["deprecated"])
async def run_observer_agent(
    request: AgentRunRequest,
    authorization: str = Header(None, alias="Authorization")
):
    """DEPRECATED: Use /ai/think instead."""
    return await ai_think(AIThinkRequest(message=request.input_text, intent="analysis"), authorization)


@router.post("/agent/briefing", tags=["deprecated"])
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
    
    logger.info(f"Streaming chat request received from user: {request.user_id} | Message: {request.message[:50]}...")
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
        # Execute guardrail check first
        guardrail_result = check_guardrails(request.message)
        if guardrail_result.blocked:
            logger.warning(f"Guardrail blocked request: {guardrail_result.reason} - {guardrail_result.details}")
            return success_response(
                data={
                    "response": f"⚠️ Request blocked by security filter.\n\nReason: {guardrail_result.reason}\n\nIf this is a false positive, please rephrase your query.",
                    "guardrail_triggered": True,
                    "guardrail_reason": guardrail_result.reason
                },
                message="Request blocked by guardrail"
            )
        
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
                reply_to_message_id=None,  # Disable reply threading as per user request
                message_thread_id=request.telegram_thread_id  # Keep in the same forum topic
            )
        
        return success_response(
            data=result,
            message="Message processed by Strategy Advisor"
        )
        
    except Exception as e:
        logger.error(f"Error in strategy chat: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent Error: {str(e)}")

@router.post("/agent/memory/sync")
async def sync_episodic_memory(authorization: str = Header(None, alias="Authorization")):
    """
    Triggers the Episodic Memory Agent to scan for unanalyzed trades and extract lessons.
    Usually called via an internal Cron job.
    """
    # Requires initialization in main.py (services["episodic_memory"])
    if "episodic_memory" not in services or not services["episodic_memory"]:
        raise HTTPException(status_code=503, detail="Episodic Memory Agent unavailable")
    
    try:
        # Since this is a background job acting on behalf of the system,
        # we don't necessarily extract an auth_token for the user, 
        # but the agent itself will use the internal system token via its tool.
        result = await services["episodic_memory"].run()
        
        return success_response(
            data={"output": result},
            message="Episodic Memory Sync Completed"
        )
    except Exception as e:
        logger.error(f"Error executing Episodic Memory Sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/universal/run")
async def run_universal_agent(
    request: UniversalAgentRunRequest
):
    """
    Run a dynamic agent based on the provided configuration.
    """
    try:
        agent = UniversalAgent(request.config)
        result = await agent.run(request.input_text, user_id=request.user_id)
        return success_response(data=result)
    except Exception as e:
        logger.error(f"Error executing Universal Agent: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/skill-creator/run")
async def run_skill_creator(
    request: SkillCreatorRunRequest
):
    """
    Run the specialized Skill Creator Agent to draft and save new skills.
    """
    if "skill_creator" not in services or not services["skill_creator"]:
        raise HTTPException(status_code=503, detail="Skill Creator Agent unavailable")
    
    try:
        result = await services["skill_creator"].run(request.user_intent, user_id=request.user_id)
        return success_response(data=result)
    except Exception as e:
        logger.error(f"Error executing Skill Creator: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/agent/post-mortem/analyze")
async def analyze_trade_post_mortem(
    trade_data: Dict[str, Any] = Body(...),
    user_id: str = "default_user",
    authorization: str = Header(None, alias="Authorization")
):
    """
    Directly run post-mortem analysis on a closed trade.
    """
    if "post_mortem" not in services or not services["post_mortem"]:
        raise HTTPException(status_code=503, detail="Post-Mortem Agent unavailable")
    
    try:
        result = await services["post_mortem"].analyze_trade(trade_data, user_id=user_id)
        return success_response(data=result)
    except Exception as e:
        logger.error(f"Post-Mortem API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/entry-reason/analyze")
async def analyze_trade_entry_reason(
    trade_data: Dict[str, Any] = Body(...),
    user_id: str = "default_user",
    authorization: str = Header(None, alias="Authorization")
):
    """
    Directly run entry-reason analysis on a new trade fill.
    """
    if "entry_reason" not in services or not services["entry_reason"]:
        raise HTTPException(status_code=503, detail="Entry Reason Agent unavailable")
    
    try:
        result = await services["entry_reason"].summarize_reason(trade_data)
        return success_response(data=result)
    except Exception as e:
        logger.error(f"Entry-Reason API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
