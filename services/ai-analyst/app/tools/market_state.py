from typing import Any, Optional
import aiohttp
import logging
from app.core.config import settings
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class MarketStateTool(BaseTool):
    name: str = "market_state"
    description: str = "Fetches institutional-grade market state features (Regime, Fakeout, Risk) for XAUUSD. Input: {'symbol': 'XAUUSD', 'timeframe': 'H1'}."

    async def run(self, input_data: Any = None, auth_token: str = None) -> str:
        symbol = "XAUUSD"
        timeframe = "H1"
        
        # Handle flexible input (string or dict)
        if isinstance(input_data, str) and input_data:
            symbol = input_data
        elif isinstance(input_data, dict):
            symbol = input_data.get("symbol", "XAUUSD")
            timeframe = input_data.get("timeframe", "H1")

        async with aiohttp.ClientSession() as session:
            try:
                headers = {}
                if auth_token:
                    if not auth_token.startswith("Bearer "):
                        headers["Authorization"] = f"Bearer {auth_token}"
                    else:
                        headers["Authorization"] = auth_token
                
                # Call API Gateway market-regime endpoint (Proxies to Strategy Core)
                # Query param for timeframe
                url = f"{settings.API_GATEWAY_URL}/api/v1/analysis/market-regime/{symbol}"
                params = {"timeframe": timeframe}
                
                async with session.get(url, params=params, headers=headers) as resp:
                     if resp.status == 200:
                         data = await resp.json()
                         ctx = data.get("data", {})
                         
                         # Parse Adaptive Guardrails Data
                         regime = ctx.get("regime", "UNSTABLE")
                         score = ctx.get("regime_score", 0.0)
                         fakeout = ctx.get("fakeout_type")
                         # Use multiplier if available, else fallback
                         risk_mult = ctx.get("risk_multiplier", ctx.get("recommended_risk", 1.0))
                         
                         fakeout_text = "None"
                         if fakeout:
                             fakeout_text = f"⚠️ {fakeout} (Trap Detected)"
                         
                         # Interpret Risk
                         risk_advice = "STANDARD"
                         if risk_mult < 1.0: risk_advice = "REDUCED SIZE (CAUTION)"
                         elif risk_mult > 1.0: risk_advice = "AGGRESSIVE (HIGH PROB)"
                         
                         report = (
                             f"--- Adaptive Market State ({symbol} {timeframe}) ---\n"
                             f"- Regime: {regime} (ADX: {score:.1f})\n"
                             f"- Fakeout/Trap: {fakeout_text}\n"
                             f"- **Dynamic Risk**: {risk_mult}x ({risk_advice})\n"
                             f"- Context: The market is {regime.split('_')[0].lower()} with {fakeout_text.lower() if fakeout else 'no'} traps."
                         )
                         return report
                     else:
                         return f"Market state unavailable ({resp.status}): {await resp.text()}"
            except Exception as e:
                logger.error(f"Failed to fetch market state: {e}")
                return f"Institutional analysis tool error: {e}"
