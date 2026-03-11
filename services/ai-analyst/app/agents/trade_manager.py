import logging
import json
import asyncio
from typing import List, Dict, Any, Optional
from app.services.gemini import GeminiClient
from app.core.config import settings
from app.core.workflow import registry

logger = logging.getLogger(__name__)

class TradeManagementAgent:
    """
    AI Agent responsible for 'Dynamic SL/TP' (Institutional Management).
    Decides when to move SL to breakeven, trail SL, or adjust TP based on 
    real-time market context and price action.
    """
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client

    async def manage_trades(self, trades: List[Dict[str, Any]], market_context: str, auth_token: str = None) -> List[Dict[str, Any]]:
        """
        Analyzes a list of open trades and executes modifications if warranted.
        
        Args:
            trades: List of open trades (standard format).
            market_context: String description of current market conditions (SMC, Volatility, etc).
            auth_token: Optional authentication token.
        """
        if not trades:
            logger.info("TradeManager: No open trades to manage.")
            return []

        # 1. Prepare trade summary for the LLM
        trade_summary = []
        for t in trades:
            trade_summary.append({
                "broker_trade_id": t.get("broker_trade_id") or t.get("id"),
                "symbol": t.get("symbol") or t.get("instrument"),
                "direction": t.get("direction") or t.get("side"),
                "entry_price": t.get("entry_price") or t.get("price"),
                "current_price": t.get("current_price") or t.get("price"), # Fallback if current not provided
                "sl": t.get("sl_price") or t.get("sl"),
                "tp": t.get("tp_price") or t.get("tp"),
                "pnl_usd": t.get("pnl_usd") or t.get("pnl", 0.0),
                "broker_account_id": t.get("broker_account_id")
            })

        prompt = f"""
        You are the 'Trade Management Agent' for MTF Olympus.
        Your goal is active risk management. You must preserve capital by securing profits 
        via Breakeven (BE) moves or Trailing SL once a trade progresses favorably.

        **Market Context:**
        {market_context}

        **Open Trades:**
        {json.dumps(trade_summary, indent=2)}

        **Your Directives:**
        1. **Breakeven (BE)**: Move SL to Entry Price + commission buffer if the trade is in profit and 
           market shows potential reversal at a supply/demand zone.
        2. **Trail SL**: If a trade is trending strongly, trail SL behind the last local swing low (for LONG) 
           or swing high (for SHORT).
        3. **Adjust TP**: If market intelligence suggests a significant institutional target further than 
           the current TP, you may extend it.
        4. **Clinical Neutrality**: If a trade is healthy and plan is valid, NO_ACTION.

        **Output JSON only:**
        {{
            "decisions": [
                {{
                    "broker_trade_id": "...",
                    "broker_account_id": "...",
                    "action": "MOVE_TO_BE | TRAIL_SL | ADJUST_TP | NO_ACTION",
                    "sl_price": 1234.56,
                    "tp_price": 1234.56,
                    "reason": "..."
                }}
            ]
        }}
        """

        try:
            response = await self.gemini.generate_content(
                # Use model fallback chain
                model=[self.gemini.model_id, "gemini-2.5-flash", "gemini-2.0-flash"],
                contents=[prompt],
                config={"response_mime_type": "application/json"}
            )
            
            raw_text = response.get("text", "{}")
            result = json.loads(raw_text)
            decisions = result.get("decisions", [])
            
            # 2. Execute decisions using ModifyTradeTool via registry
            execution_results = []
            modify_tool = registry.get("modify_trade")
            
            if not modify_tool:
                logger.error("TradeManager: 'modify_trade' tool not found in registry.")
                return [{"error": "Modify tool not available"}]
            
            for dec in decisions:
                if dec.get("action") == "NO_ACTION":
                    continue
                
                logger.info(f"TradeManager: Executing {dec['action']} for trade {dec['broker_trade_id']}")
                
                # Call tool
                tool_input = {
                    "broker_account_id": dec.get("broker_account_id"),
                    "broker_trade_id": dec.get("broker_trade_id"),
                    "sl_price": dec.get("sl_price"),
                    "tp_price": dec.get("tp_price"),
                    "is_position": True
                }
                
                res = await modify_tool.run_tool(tool_input, auth_token=auth_token)
                execution_results.append({
                    "trade_id": dec["broker_trade_id"],
                    "action": dec["action"],
                    "result": res,
                    "reason": dec.get("reason")
                })
                
            return execution_results

        except Exception as e:
            logger.error(f"TradeManager failed: {e}")
            return [{"error": str(e)}]
