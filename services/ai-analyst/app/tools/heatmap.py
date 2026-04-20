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
        
        symbol = "XAUUSD"
        if hasattr(input_data, "dict"):
            input_data = input_data.dict()
            
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", "XAUUSD")
        elif isinstance(input_data, str):
            symbol = input_data

        auth_token = kwargs.get("auth_token")
        strategy_core_url = f"{settings.STRATEGY_CORE_URL}/api/v1"
        
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}" if not auth_token.startswith("Bearer ") else auth_token

        async with aiohttp.ClientSession() as session:
            try:
                # 1. Fetch Current Spot Price
                current_price = 0.0
                try:
                    redis_url = settings.REDIS_URL
                    redis_client = redis.from_url(redis_url, decode_responses=True)
                    spot_data = await redis_client.hgetall(f"market_data:spot:{symbol}")
                    if spot_data and "bid" in spot_data:
                        bid = float(spot_data.get("bid", 0))
                        ask = float(spot_data.get("ask", 0))
                        current_price = (bid + ask) / 2.0 if ask > 0 else bid
                    await redis_client.close()
                except Exception as e:
                    logger.warning(f"Redis price fetch failed: {e}")

                # 2. Fetch Gamma Levels (V3.0)
                url = f"{strategy_core_url}/analysis/gamma/levels"
                params = {"symbol": symbol}
                if current_price > 0:
                    params["current_price"] = str(current_price)

                async with session.get(url, params=params, headers=headers, timeout=120.0) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        regime_data = data.get("regime", {})
                        is_valid = regime_data.get("is_valid", True)
                        alerts = regime_data.get("integrity_alerts", [])
                        
                        # V3.0 Fragility & Macro
                        lfi = regime_data.get("fragility_index", 0.0)
                        f_alert = regime_data.get("fragility_alert", "STABLE")
                        macro = data.get("macro_context") or {}
                        
                        heatmap = data.get("heatmap") or []
                        max_pain = data.get("max_pain") or 0.0
                        underlying = data.get("underlying_price") or current_price or 0.0
                        
                        if not is_valid:
                            alert_text = ", ".join(alerts) if alerts else "STALE_DATA"
                            return f"### ⚠️ Institutional Data Integrity Alert: {alert_text}\n\n" \
                                   f"The liquidity regime logic has triggered an integrity gate. Reference Spot: {underlying:.2f}"

                        spot_label = f"{underlying:.2f}" if underlying > 0 else "N/A"
                        report = [f"### 🌡️ Gold Liquidity Heatmap (Spot: {spot_label})"]
                        
                        # 3. V3.0 Macro Header
                        if macro:
                            ry = macro.get('real_yield_10y')
                            dxy = macro.get('dxy_index')
                            ry_str = f"{ry:.2f}%" if ry is not None else "N/A"
                            dxy_str = f"{dxy:.2f}" if dxy is not None else "N/A"
                            report.append(f"> **Macro Context**: US 10Y Real Yield: {ry_str} | DXY: {dxy_str}")
                            report.append(f"> **Liquidity Fragility Index (LFI)**: `{lfi:.1f}/100` — **{f_alert}**")

                        report.append(f"\n**Max Pain (Gravity Center): {max_pain:.2f}**")
                        report.append("\n| Strike | Relative Density | Actionable Bias | Greeks (V3.0) |")
                        report.append("| :--- | :--- | :--- | :--- |")
                        
                        sorted_heatmap = sorted(heatmap, key=lambda x: x['strike'], reverse=True)
                        if underlying > 0:
                            sorted_heatmap = [h for h in sorted_heatmap if abs(h['strike'] - underlying) <= 500]
                        
                        for entry in sorted_heatmap:
                            density = entry.get('relative_density', 0.0)
                            strike = entry.get('strike', 0.0)
                            bar_len = int(density * 10)
                            bar = "█" * bar_len + "░" * (10 - bar_len)
                            
                            # Greeks (V3.0)
                            iv = entry.get('iv', 0.0)
                            vanna = entry.get('vanna', 0.0)
                            
                            bias = "Resistance" if strike > underlying else "Support"
                            greeks_str = f"IV: {iv*100:.1f}%"
                            
                            if max_pain > 0 and abs(strike - max_pain) < 25:
                                bias = "🎯 **MAGNET**"
                                greeks_str += f" | Van: {vanna:.1e}"
                                
                            report.append(f"| {strike:.2f} | {bar} ({density*100:.0f}%) | {bias} | {greeks_str} |")
                        
                        report.append("\n> **Interpretation**: High LFI (>70) indicates 'Liquidity Fragility' where walls may collapse (Gamma-Trap). Vanna exposure at Magnet zones indicates dealer hedging pressure.")
                        return "\n".join(report)
                    else:
                        return f"Failed to fetch heatmap data ({resp.status})"
            except Exception as e:
                logger.error(f"Heatmap Tool Failed: {repr(e)}")
                return f"Heatmap Tool Error: {repr(e)}"

