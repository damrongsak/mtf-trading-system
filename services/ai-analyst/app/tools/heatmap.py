import logging
import json
import os
import redis.asyncio as redis
from typing import Any, Optional, Type
import aiohttp
from pydantic import BaseModel, Field
from app.core.config import settings
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class HeatmapInput(BaseModel):
    symbol: str = Field(default="XAUUSD", description="The financial instrument symbol (e.g., XAUUSD).")

class LiquidityHeatmapTool(BaseTool):
    name: str = "liquidity_heatmap"
    description: str = """
    Provides a spatial view of Gold (XAUUSD) liquidity density (Heatmap).
    Identifies 'Gravity Zones' where price is likely to be pinned or rejected.
    """
    args_schema: Type[BaseModel] = HeatmapInput
    is_heavy: bool = True # Heatmap fetch and price check involve multiple IO layers

    async def run_tool(self, input_data: Any, **kwargs) -> str:
        logger.info(f"DEBUG HEATMAP: input_data={input_data} ({type(input_data)})")
        logger.info(f"DEBUG HEATMAP: kwargs={kwargs}")
        
        symbol = "XAUUSD"
        if hasattr(input_data, "dict"):
            input_data = input_data.dict()
            
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", "XAUUSD")
        elif isinstance(input_data, str):
            symbol = input_data

        logger.info(f"DEBUG HEATMAP: FINAL symbol={symbol} ({type(symbol)})")

        # Standardize auth_token extraction from kwargs or context
        auth_token = kwargs.get("auth_token")
        
        strategy_core_url = f"{settings.STRATEGY_CORE_URL}/api/v1"
        
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}" if not auth_token.startswith("Bearer ") else auth_token

        async with aiohttp.ClientSession() as session:
            try:
                # 1. Fetch Current Spot Price — Multi-layer fallback for reliability
                current_price = 0.0
                
                # Layer 0: Direct Redis Fetch (Fastest - New Hash Cache)
                try:
                    redis_url = settings.REDIS_URL
                    redis_client = redis.from_url(redis_url, decode_responses=True)
                    
                    spot_data = await redis_client.hgetall(f"market_data:spot:{symbol}")
                    if spot_data and "bid" in spot_data:
                        bid = float(spot_data.get("bid", 0))
                        ask = float(spot_data.get("ask", 0))
                        current_price = (bid + ask) / 2.0 if ask > 0 else bid
                        logger.info(f"Fetched live spot price from L2 Cache: {current_price}")
                    else:
                        features_json = await redis_client.get(f"features:{symbol}:M15")
                        if features_json:
                            features_data = json.loads(features_json)
                            close_array = features_data.get("columns", [])
                            if "close" in close_array:
                                close_idx = close_array.index("close")
                                data_index = features_data.get("data", [])
                                if data_index and len(data_index) > 0:
                                    current_price = float(data_index[-1][close_idx])
                                    logger.info(f"Fetched spot price from legacy Redis (features): {current_price}")

                    await redis_client.close()
                except Exception as e:
                    logger.warning(f"Layer 0 (Redis) price fetch failed: {e}")

                # Layer 1: data-pipeline candles (primary fallback)
                if current_price <= 0:
                    try:
                        data_pipeline_url = f"{settings.DATA_PIPELINE_URL}/api/v1"
                        price_url = f"{data_pipeline_url}/candles"
                        price_params = {"symbol": symbol, "timeframe": "H1", "page_size": 1}
                        async with session.get(price_url, params=price_params, headers=headers, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                            if resp.status == 200:
                                candle_data = await resp.json()
                                candles = candle_data.get("data", [])
                                if candles:
                                    current_price = float(candles[0].get("close") or 0.0)
                    except Exception as e:
                        logger.warning(f"Layer 1 (data-pipeline) price fetch failed: {e}")

                # 2. Fetch Gamma Levels
                url = f"{strategy_core_url}/analysis/gamma/levels"
                params = {"symbol": symbol}
                if current_price > 0:
                    params["current_price"] = str(current_price)

                async with session.get(url, params=params, headers=headers, timeout=120.0) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        heatmap = data.get("heatmap") or []
                        max_pain = data.get("max_pain") or 0.0
                        underlying = data.get("underlying_price") or current_price or 0.0
                        
                        if not heatmap:
                            return "No liquidity heatmap data available currently."
                        
                        spot_label = f"{underlying:.2f}" if underlying > 0 else "N/A"
                        report = [f"### 🌡️ Gold Liquidity Heatmap (Spot: {spot_label})"]
                        report.append(f"\n**Max Pain (Gravity Center): {max_pain:.2f}**")
                        if underlying > 0:
                            report.append(f"> Reference spot price: {underlying:.2f} | CME Options Strikes mapped relative to spot")
                        report.append("\n| Strike | Relative Density | Actionable Bias |")
                        report.append("| :--- | :--- | :--- |")
                        
                        sorted_heatmap = sorted(heatmap, key=lambda x: x['strike'], reverse=True)
                        if underlying > 0:
                            sorted_heatmap = [
                                h for h in sorted_heatmap 
                                if abs(h['strike'] - underlying) <= 500
                            ]
                        
                        for entry in sorted_heatmap:
                            density = entry.get('relative_density', 0.0)
                            strike = entry.get('strike', 0.0)
                            bar_len = int(density * 10)
                            bar = "█" * bar_len + "░" * (10 - bar_len)
                            
                            bias = "Neutral"
                            if underlying > 0:
                                if strike > underlying:
                                    bias = "Resistance (Calls)"
                                else:
                                    bias = "Support (Puts)"
                                    
                            if max_pain > 0 and abs(strike - max_pain) < 25:
                                bias = "🎯 **MAGNET ZONE**"
                                
                            report.append(f"| {strike:.2f} | {bar} ({density*100:.0f}%) | {bias} |")
                        
                        report.append("\n> **Interpretation**: Areas with >70% density represent institutional 'walls'. Price tends to be sucked towards Max Pain during option expiry.")
                        return "\n".join(report)
                    else:
                        return f"Failed to fetch heatmap data ({resp.status})"
            except Exception as e:
                logger.error(f"Heatmap Tool Failed: {repr(e)}")
                return f"Heatmap Tool Error: {repr(e)}"
