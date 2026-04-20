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

        strategy_core_url = f"{settings.STRATEGY_CORE_URL}/api/v1"
        
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
                    if spot_data and ("bid" in spot_data or "price" in spot_data):
                        bid = float(spot_data.get("bid", spot_data.get("price", 0)))
                        ask = float(spot_data.get("ask", bid))
                        current_price = (bid + ask) / 2.0 if ask > 0 else bid
                    await redis_client.close()
                except Exception as e:
                    logger.warning(f"Redis spot lookup failed: {e}")

                # 2. Fetch Gamma Levels (V3.0)
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

                # 3. Build V3.0 Report
                raw_futures = float(underlying_futures or 0.0)
                raw_spot = float(current_price or 0.0)
                max_pain = float(g_data.get("max_pain", 0.0))
                g_regime = g_data.get("regime", {})
                is_valid = g_regime.get("is_valid", True)
                alerts = g_regime.get("integrity_alerts", [])
                
                # V3.0 Greeks & Fragility
                lfi = float(g_regime.get("fragility_index", 0.0))
                f_alert = g_regime.get("fragility_alert", "STABLE")
                vanna_exp = float(g_regime.get("total_vanna_exposure", 0.0))
                charm_decay = float(g_regime.get("total_charm_decay", 0.0))
                
                report = []
                if not is_valid:
                    alert_str = ", ".join(alerts) if alerts else "STALE_DATA"
                    report.append(f"⚠️ **DATA_INTEGRITY_ALERT**: Institutional Gamma regime is currently INVALID ({alert_str}).")

                report.extend([
                    f"**Institutional OI Analysis ({actual_snapshot_at})**",
                    f"Spot: ${raw_spot:.2f} | Futures: ${raw_futures:.2f} | Max Pain: ${max_pain:.2f}",
                    f"Gamma Regime: {g_regime.get('regime', 'UNKNOWN')} (Flip: {g_regime.get('gamma_flip_level', 'N/A')})",
                    f"\n**V3.0 Liquidity Metrics**:",
                    f"- **Fragility Index (LFI)**: `{lfi:.1f}/100` ({f_alert})",
                    f"- **Vanna Exposure**: {vanna_exp:.2e} (Delta sensitivity to Vol)",
                    f"- **Charm Decay**: {charm_decay:.2e} (Delta sensitivity to Time)",
                    "\n**Strategic Liquidity Zones**:"
                ])
                
                if gamma_levels:
                    # Sort by significance and take top 8
                    for lvl in sorted(gamma_levels, key=lambda x: x.get("significance_score", 0), reverse=True)[:8]:
                        z_type = lvl.get("zone_type", "MAJOR")
                        action = lvl.get("market_action", "PIVOT")
                        price_val = float(lvl.get("price", 0.0))
                        iv = lvl.get("iv", 0.0)
                        vanna = lvl.get("vanna", 0.0)
                        
                        greek_info = f" [IV: {iv*100:.1f}%, Van: {vanna:.1e}]"
                        report.append(f"- ${price_val:.2f} [{z_type}/{action}] | Significance: {lvl.get('significance_score', 0):.2f}{greek_info}")
                else:
                    report.append("No major zones detected.")
                
                return "\n".join(report)

            except Exception as e:
                logger.error(f"OpenInterestTool error: {e}")
                return f"Error: {str(e)}"


