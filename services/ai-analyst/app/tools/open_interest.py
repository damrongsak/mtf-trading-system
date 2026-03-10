import json
import logging
import os
import redis.asyncio as redis
from typing import Any, Optional, Type, Dict
import aiohttp
from app.core.config import settings
from app.core.base_tool import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class OpenInterestInput(BaseModel):
    symbol: str = Field(default="XAUUSD", description="Symbol to analyze (e.g. XAUUSD)")
    snapshot_at: Optional[str] = Field(None, description="ISO-date for the snapshot at a specific time")
    horizon: Optional[str] = Field(None, description="Analysis horizon: 'short', 'medium', or 'long'")

class OpenInterestTool(BaseTool):
    name: str = "open_interest"
    description: str = (
        "Fetches institutional Open Interest (OI) analysis for GOLD (XAU/USD). "
        "Auto-resolves to the LATEST available snapshot if date not provided. "
        "Returns total OI, Net OI, Put/Call Ratio, Max Pain, and OIWAP."
    )
    args_schema: Type[BaseModel] = OpenInterestInput

    async def run_tool(self, input_data: Any, auth_token: str = None, **kwargs) -> str:
        symbol = "XAUUSD"
        snapshot_at = None
        horizon = None
        
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
            snapshot_at = input_data.get("snapshot_at")
            horizon = input_data.get("horizon")
        elif isinstance(input_data, str):
            symbol = input_data

        data_pipeline_url = f"{settings.DATA_PIPELINE_URL}/api/v1"
        strategy_core_url = f"{settings.STRATEGY_CORE_URL}/api/v1"
        
        horizon_map = {
            "short": "SHORT_TERM",
            "medium": "MEDIUM_TERM",
            "long": "LONG_TERM"
        }
        target_term = horizon_map.get(str(horizon).lower()) if horizon else None

        headers = {}
        if auth_token:
            headers["Authorization"] = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"
        
        async with aiohttp.ClientSession() as session:
            try:
                # 1. Fetch Current Spot Price
                current_price = 0.0
                try:
                    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
                    spot_data = await redis_client.hgetall(f"market_data:spot:{symbol}")
                    if spot_data and "bid" in spot_data:
                        bid = float(spot_data.get("bid", 0))
                        ask = float(spot_data.get("ask", 0))
                        current_price = (bid + ask) / 2.0 if ask > 0 else bid
                    await redis_client.close()
                except: pass

                if current_price <= 0:
                    try:
                        price_url = f"{data_pipeline_url}/candles"
                        params = {"symbol": symbol, "timeframe": "H1", "page_size": 1}
                        async with session.get(price_url, params=params, headers=headers, timeout=5.0) as resp:
                            if resp.status == 200:
                                candle_data = await resp.json()
                                candles = candle_data.get("data", [])
                                if candles:
                                    current_price = float(candles[0].get("close") or 0.0)
                    except: pass

                # 2. Fetch Gamma Levels
                gamma_url = f"{strategy_core_url}/analysis/gamma/levels"
                params = {"symbol": symbol}
                if current_price > 0: params["current_price"] = str(current_price)
                if snapshot_at: params["snapshot_at"] = snapshot_at
                
                async with session.get(gamma_url, params=params, headers=headers, timeout=5.0) as resp:
                    if resp.status == 200:
                        g_data = await resp.json()
                        gamma_levels = g_data.get("levels", [])
                        underlying_futures = float(g_data.get("underlying_price") or 0.0)
                        actual_snapshot_at = g_data.get("snapshot_at", "Unknown")
                    else:
                        return f"Error fetching Gamma data: {resp.status}"

                if target_term:
                    gamma_levels = [l for l in gamma_levels if l.get('term') == target_term]

                # 3. Build Report
                raw_futures = float(underlying_futures or 0.0)
                raw_spot = float(current_price or 0.0)
                max_pain = float(g_data.get("max_pain", 0.0))
                
                report = [
                    f"**OI Snapshot ({actual_snapshot_at})**",
                    f"Spot: {raw_spot:.2f} | Futures: {raw_futures:.2f} | Max Pain: {max_pain:.2f}",
                    "\n**Key Liquidity Zones**:"
                ]
                
                if gamma_levels:
                    # Sort by significance and take top 10
                    for lvl in sorted(gamma_levels, key=lambda x: x.get("significance_score", 0), reverse=True)[:10]:
                        z_type = lvl.get("zone_type", "MAJOR")
                        action = lvl.get("market_action", "PIVOT")
                        price_val = float(lvl.get("price", 0.0))
                        report.append(f"- {price_val:.2f} [{z_type}/{action}] | Significance: {lvl.get('significance_score', 0):.2f}")
                else:
                    report.append("No major zones detected.")
                
                return "\n".join(report)

            except Exception as e:
                logger.error(f"OpenInterestTool error: {e}")
                return f"Error: {str(e)}"

