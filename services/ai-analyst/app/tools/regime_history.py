import json
import logging
import aiohttp
from typing import Any, Optional, Type, List
from app.core.config import settings
from app.core.base_tool import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class RegimeHistoryInput(BaseModel):
    symbol: str = Field(default="XAUUSD", description="Symbol to analyze (e.g. XAUUSD)")
    limit: int = Field(default=20, description="Number of historical records to fetch")

class RegimeHistoryTool(BaseTool):
    name: str = "get_regime_history"
    description: str = (
        "Fetches historical institutional GEX regimes (H4 resolution) for an asset. "
        "Provides context on whether the market is in a Positive Gamma (Stable) or Negative Gamma (Volatile) state. "
        "Useful for understanding regime shifts over time."
    )
    args_schema: Type[BaseModel] = RegimeHistoryInput

    async def run_tool(self, input_data: Any, auth_token: str = None, **kwargs) -> str:
        symbol = "XAUUSD"
        limit = 20
        
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
            limit = input_data.get("limit", limit)
        elif isinstance(input_data, str):
            symbol = input_data

        strategy_core_url = f"{settings.STRATEGY_CORE_URL}/api/v1"
        
        headers = {}
        if auth_token:
            headers["Authorization"] = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"
        
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{strategy_core_url}/analysis/gamma/regime-history"
                params = {"symbol": symbol, "limit": limit}
                
                async with session.get(url, params=params, headers=headers, timeout=5.0) as resp:
                    if resp.status == 200:
                        history = await resp.json()
                        
                        if not history:
                            return f"No regime history found for {symbol}."
                            
                        report = [f"### Institutional Regime History: {symbol}"]
                        for entry in history:
                            ts = entry.get("timestamp")
                            gex = entry.get("gex_proxy", 0)
                            regime = entry.get("regime_type", "UNKNOWN")
                            is_noise = entry.get("is_noise", False)
                            status = "NOISE" if is_noise else regime
                            
                            report.append(f"- {ts}: {status} | GEX: {gex:.2e}")
                            
                        return "\n".join(report)
                    else:
                        return f"Error fetching regime history: {resp.status}"

            except Exception as e:
                logger.error(f"RegimeHistoryTool error: {e}")
                return f"Error: {str(e)}"
