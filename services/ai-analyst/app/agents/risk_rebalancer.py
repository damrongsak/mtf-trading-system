import logging
import json
import asyncio
from typing import List, Dict, Any, Optional
from app.services.gemini import GeminiClient
from app.core.config import settings
from app.core.workflow import registry, AgentState

logger = logging.getLogger(__name__)

class RiskRebalancerAgent:
    """
    AI Agent responsible for 'Dynamic Risk Rebalancing' (Institutional Phase 57).
    Analyzes market regimes, news sentiment, and fund health to recommend 
    adjustments to drawdown thresholds and risk percentages.
    """
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client

    async def analyze_risk(self, state: AgentState) -> AgentState:
        """
        Main entry point for LangGraph risk rebalancing node.
        """
        last_message = state["messages"][-1].content
        
        # 1. Fetch Tools
        risk_tool = registry.get("risk_review")
        market_tool = registry.get("get_market_context")
        search_tool = registry.get("google_search")
        
        if not all([risk_tool, market_tool]):
            state["scratchpad"].append("RiskRebalancer: Missing required tools (risk_review or market_context).")
            return state

        # 2. Extract potential Fund ID from message or state
        # (For this MVP, we assume the user provides it or it's in state)
        fund_id = state.get("active_fund_id")
        if not fund_id and "fund" in last_message.lower():
            # Basic extraction - in production use a better extractor
            import re
            match = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', last_message.lower())
            if match:
                fund_id = match.group(0)

        if not fund_id:
            state["scratchpad"].append("RiskRebalancer: No Fund ID identified for analysis.")
            return state

        # 3. Gather Data
        risk_data = await risk_tool.run_tool({"fund_id": fund_id})
        market_data = await market_tool.run_tool("XAUUSD") # Default symbols for now
        
        prompt = f"""
        You are the 'Institutional Risk Rebalancer' for MTF Olympus.
        Your goal is to adjust fund risk parameters based on market volatility and regime.

        **Current Fund Risk Configuration:**
        {risk_data}

        **Market Context:**
        {market_data}

        **User Message:**
        {last_message}

        **Your Directives:**
        1. **Volatility Scaling**: If market volatility is extreme (ATR spike), recommend lowering `risk_percentage`.
        2. **Regime Awareness**: If in a choppy range, tighten `max_drawdown_threshold`.
        3. **FOMC/News Protection**: If high-impact news is imminent, suggest a 'Guard Mode' (lower risk).
        4. **Clinical Objective**: If risk levels are appropriate for the regime, NO_ACTION.

        **Output JSON only:**
        {{
            "analysis": "Brief reasoning...",
            "recommendation": {{
                "risk_percentage": 0.005,
                "max_drawdown_threshold": 4.5
            }},
            "action": "REBALANCE | NO_ACTION",
            "reason": "..."
        }}
        """

        try:
            response = await self.gemini.client.aio.models.generate_content(
                model=self.gemini.model_id,
                contents=prompt
            )
            
            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:-3]
            
            result = json.loads(raw_text)
            
            if result.get("action") == "REBALANCE":
                rec = result.get("recommendation", {})
                state["scratchpad"].append(f"RiskRebalancer suggests rebalance: {json.dumps(rec)}")
                state["messages"].append({"role": "assistant", "content": f"I've analyzed the risk profile for Fund {fund_id}. Based on the current market regime, I recommend: \n- Risk Percentage: {rec.get('risk_percentage', 0)*100:.2f}%\n- Drawdown Threshold: {rec.get('max_drawdown_threshold', 0):.2f}\n\nReason: {result.get('reason')}"})
            else:
                state["messages"].append({"role": "assistant", "content": "Current risk parameters are optimized for the observed market conditions. No rebalancing required."})

        except Exception as e:
            logger.error(f"RiskRebalancer failed: {e}")
            state["scratchpad"].append(f"RiskRebalancer Error: {str(e)}")
            
        return state
