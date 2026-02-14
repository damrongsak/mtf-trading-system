import json
import logging
from typing import Any, Optional
import aiohttp
from app.core.config import settings
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class OpenInterestTool(BaseTool):
    name: str = "open_interest"
    description: str = """
    Fetches institutional Open Interest (OI) analysis for GOLD (XAU/USD).
    Auto-resolves to the LATEST available snapshot if date not provided.
    Input JSON: {"snapshot_at": "ISO-date", "contract": "optional-contract"}
    Returns total OI, Net OI, Put/Call Ratio, Max Pain, and OIWAP.
    """

    async def run(self, input_data: Any = None, auth_token: str = None) -> str:
        url_base = f"{settings.API_GATEWAY_URL}/api/v1"
        
        # Prepare Headers
        headers = {}
        if auth_token:
            if not auth_token.startswith("Bearer "):
                headers["Authorization"] = f"Bearer {auth_token}"
            else:
                headers["Authorization"] = auth_token
        
        async with aiohttp.ClientSession() as session:
            try:
                # 1. Fetch Current Spot Price for XAUUSD (Dynamic from Candles)
                current_price = 0.0
                try:
                    # Fetch last H1 candle to get the most recent price (M1 might be sparse)
                    price_url = f"{url_base}/market/candles"
                    params = {"symbol": "XAUUSD", "timeframe": "H1", "count": 1, "data_source": "CTRADER"}
                    async with session.get(price_url, params=params, headers=headers, timeout=5.0) as resp:
                        if resp.status == 200:
                            candle_data = await resp.json()
                            candles = candle_data.get("data", [])
                            if candles:
                                # Use the close price of the most recent M1 candle as current spot
                                current_price = float(candles[0].get("close") or 0.0)
                                logger.info(f"Fetched live spot price from candles: {current_price}")
                except Exception as e:
                    logger.warning(f"Failed to fetch live spot price from candles: {e}")

                # 2. Fetch Gamma Levels (Basis Adjusted)
                gamma_url = f"{url_base}/analysis/gamma/levels"
                params = {"symbol": "XAUUSD"}
                if current_price and current_price > 0:
                    params["current_price"] = current_price
                
                gamma_levels = []
                underlying_futures = 0.0
                snapshot_at = "Unknown"
                
                async with session.get(gamma_url, params=params, headers=headers, timeout=10.0) as resp:
                    if resp.status == 200:
                        g_resp = await resp.json()
                        g_data = g_resp.get("data", {})
                        gamma_levels = g_data.get("levels", [])
                        underlying_futures = float(g_data.get("underlying_price") or 0.0)
                        snapshot_at = g_data.get("snapshot_at", "Unknown")

                # 3. Fetch Confirmation State (Market Regime)
                confirmation_info = "RSI/EMA data unavailable"
                try:
                    regime_url = f"{url_base}/analysis/market-regime/XAUUSD"
                    async with session.get(regime_url, headers=headers, timeout=5.0) as resp:
                        if resp.status == 200:
                            r_data = await resp.json()
                            ctx = r_data.get("data", {})
                            regime = ctx.get("regime", "UNKNOWN")
                            r_score = float(ctx.get('regime_score') or 0.0)
                            confirmation_info = f"Current Regime: {regime} (ADX: {r_score:.1f})"
                except: pass

                # 4. Build the Professional Report
                raw_futures = float(underlying_futures or 0.0)
                raw_spot = float(current_price or 0.0)
                basis = raw_futures - raw_spot if raw_futures > 0 and raw_spot > 0 else 0
                
                report = [f"### 🎯 Gold Open Interest Strategy Report ({snapshot_at})"]
                report.append(f"\n> **📊 Basis Adjustment**: Gold Futures ({raw_futures:.2f}) vs Spot ({raw_spot:.2f}) | **Offset**: {basis:.2f}")
                
                if gamma_levels:
                    report.append("\n#### 🧱 Zones of Interest (Basis Adjusted)")
                    for lvl in gamma_levels:
                        z_type = lvl.get("zone_type", "MAJOR")
                        l_type = lvl.get("type", "LEVEL")
                        mapped_price = lvl.get("price", 0.0)
                        strike = lvl.get("strike", 0.0)
                        dte = lvl.get("dte")
                        confluence = lvl.get("confluence", [])
                        
                        # Highlighting
                        prefix = "🔥 " if z_type == "MAJOR" else "⚡ "
                        conf_str = f" | [Confluence: {', '.join(confluence)}]" if confluence else ""
                        dte_str = f" [DTE: {dte}]" if dte is not None else ""
                        
                        report.append(f"{prefix}**{z_type} {l_type}**: Spot **{mapped_price:.2f}** (Futures {strike:.2f}){dte_str}{conf_str}")
                else:
                    report.append("\n⚠️ No major OI liquidity zones detected for the current session.")

                report.append(f"\n#### 🛡️ Confirmation Checklist")
                at_zone = any(abs(float(l.get('price') or 0) - raw_spot) < 2.0 for l in gamma_levels) if raw_spot > 0 else False
                smc_aligned = any(l.get('confluence') for l in gamma_levels if abs(float(l.get('price') or 0) - raw_spot) < 2.0) if raw_spot > 0 else False
                
                report.append(f"- **Zone Status**: {'✅ PRICE AT ZONE' if at_zone else '⬜ APPROACHING'}")
                report.append(f"- **Institutional Alignment**: {'✅ SMC AT ZONE' if smc_aligned else '⬜ WAITING'}")
                report.append(f"- **Indicator Filter**: {confirmation_info}")
                
                report.append(f"\n> [!IMPORTANT]\n> **Execution Strategy**: Use the **Basis Adjusted Spot Levels** for your limit orders. Do not enter unless **RSI crossover** or **structure shift** occurs at these levels.")

                return "\n".join(report)

            except Exception as e:
                logger.error(f"OI Tool Failed: {e}")
                return f"OI Tool Error: {str(e)}"
