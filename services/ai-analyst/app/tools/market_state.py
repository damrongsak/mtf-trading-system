from typing import Any, Optional
import aiohttp
import logging
from app.core.config import settings
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class MarketStateTool(BaseTool):
    name: str = "market_state"
    description: str = "Fetches institutional-grade market state features (PCR, Max Pain, OI Skew, Crowding Regime) for XAUUSD."

    async def run(self, input_data: Any = None, auth_token: str = None) -> str:
        symbol = "XAUUSD"
        if isinstance(input_data, str) and input_data:
            symbol = input_data
        elif isinstance(input_data, dict) and "symbol" in input_data:
            symbol = input_data["symbol"]

        async with aiohttp.ClientSession() as session:
            try:
                headers = {}
                if auth_token:
                    headers["Authorization"] = auth_token
                
                # Call API Gateway analysis/positioning endpoint
                url = f"{settings.API_GATEWAY_URL}/api/v1/analysis/positioning/status"
                params = {"symbol": symbol}
                
                async with session.get(url, params=params, headers=headers) as resp:
                     if resp.status == 200:
                         data = await resp.json()
                         p = data.get("data", {})
                         
                         report = (
                             f"--- Institutional Positioning ({symbol}) ---\n"
                             f"- Crowd Sentiment: {p.get('crowding_regime', 'N/A')}\n"
                             f"- Put/Call Ratio: {p.get('pcr', 0.0):.2f}\n"
                             f"- OI Skew: {p.get('oi_skew_pct', 0.0):.2f}%\n"
                             f"- Max Pain: {p.get('max_pain', 0.0):.2f}\n"
                             f"- Dominant Regime: {p.get('regime', 'Neutral')}"
                         )
                         return report
                     else:
                         # Fallback to local logic or error
                         return f"Market positioning data unavailable ({resp.status})"
            except Exception as e:
                logger.error(f"Failed to fetch market state: {e}")
                return f"Institutional analysis tool error: {e}"
