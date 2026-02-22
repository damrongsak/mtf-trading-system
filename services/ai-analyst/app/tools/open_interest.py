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
        # We use direct service URLs instead of API Gateway
        data_pipeline_url = f"{settings.DATA_PIPELINE_URL}/api/v1"
        strategy_core_url = f"{settings.STRATEGY_CORE_URL}/api/v1"
        
        # Parse Inputs
        symbol = "XAUUSD"
        snapshot_at = None
        horizon = None # "short", "medium", "long"
        
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
            snapshot_at = input_data.get("snapshot_at")
            horizon = input_data.get("horizon")
        elif isinstance(input_data, str) and input_data.strip():
            if input_data.startswith("{"):
                try:
                    data = json.loads(input_data)
                    symbol = data.get("symbol", symbol)
                    snapshot_at = data.get("snapshot_at")
                    horizon = data.get("horizon")
                except: pass
            else:
                symbol = input_data.strip().upper()

        # Map horizon to term
        horizon_map = {
            "short": "SHORT_TERM",
            "medium": "MEDIUM_TERM",
            "long": "LONG_TERM"
        }
        target_term = horizon_map.get(str(horizon).lower())

        # Prepare Headers
        headers = {}
        if auth_token:
            if not auth_token.startswith("Bearer "):
                headers["Authorization"] = f"Bearer {auth_token}"
            else:
                headers["Authorization"] = auth_token
        
        async with aiohttp.ClientSession() as session:
            try:
                # 1. Fetch Current Spot Price for Symbol
                current_price = 0.0
                try:
                    price_url = f"{data_pipeline_url}/candles"
                    params = {"symbol": symbol, "timeframe": "H1", "page_size": 1}
                    async with session.get(price_url, params=params, headers=headers, timeout=5.0) as resp:
                        if resp.status == 200:
                            candle_data = await resp.json()
                            candles = candle_data.get("data", [])
                            if candles:
                                current_price = float(candles[0].get("close") or 0.0)
                                logger.info(f"Fetched live spot price from candles: {current_price}")
                except Exception as e:
                    logger.warning(f"Failed to fetch live spot price from candles: {e}")

                # 2. Fetch Gamma Levels (Basis Adjusted)
                gamma_url = f"{strategy_core_url}/analysis/gamma/levels"
                params = {"symbol": symbol}
                if current_price and current_price > 0:
                    params["current_price"] = str(current_price)
                if snapshot_at:
                    params["snapshot_at"] = snapshot_at
                
                gamma_levels = []
                underlying_futures = 0.0
                actual_snapshot_at = "Unknown"
                g_data = {} # Initialize to avoid UnboundLocalError
                
                async with session.get(gamma_url, params=params, headers=headers, timeout=30.0) as resp:
                    if resp.status == 200:
                        g_data = await resp.json()
                        gamma_levels = g_data.get("levels", [])
                        underlying_futures = float(g_data.get("underlying_price") or 0.0)
                        actual_snapshot_at = g_data.get("snapshot_at", "Unknown")

                # Filter by horizon if requested
                if target_term:
                    gamma_levels = [l for l in gamma_levels if l.get('term') == target_term]

                # 3. Fetch Confirmation State (Market Regime) - Direct from strategy-core
                confirmation_info = "RSI/EMA data unavailable"
                try:
                    # Strategy Core endpoint: POST /api/v1/market/regime
                    regime_url = f"{strategy_core_url}/market/regime"
                    regime_payload = {"symbol": "XAUUSD", "timeframe": "D1", "bias": "NEUTRAL"}
                    async with session.post(regime_url, json=regime_payload, headers=headers, timeout=5.0) as resp:
                        if resp.status == 200:
                            ctx = await resp.json()
                            regime = ctx.get("regime", "UNKNOWN")
                            r_score = float(ctx.get('regime_score') or 0.0)
                            confirmation_info = f"Current Regime: {regime} (ADX: {r_score:.1f})"
                except: pass

                # 4. Build the Professional Report
                raw_futures = float(underlying_futures or 0.0)
                raw_spot = float(current_price or 0.0)
                max_pain = float(g_data.get("max_pain", 0.0))
                basis = raw_futures - raw_spot if raw_futures > 0 and raw_spot > 0 else 0
                
                report = [f"### 🎯 Gold Open Interest Strategy Report ({actual_snapshot_at})"]
                if horizon:
                    report.append(f"**Horizon Focus**: {horizon.capitalize()}-Term")

                report.append(f"\n- **Futures Price**: {raw_futures:.2f} | **Spot Base**: {raw_spot:.2f}")
                report.append(f"- **Institutional Anchor (Max Pain)**: {max_pain:.2f}")
                report.append(f"\n> **📊 Basis Adjustment**: Offset is {basis:+.2f} pts")
                
                if gamma_levels:
                    report.append("\n#### 🧱 Significant Liquidity Zones (Basis Adjusted)")
                    # Group by term for display
                    terms = ["SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"]
                    for t in terms:
                        term_levels = [l for l in gamma_levels if l.get('term') == t]
                        if term_levels:
                            t_display = t.replace("_", " ").title()
                            report.append(f"\n**{t_display}**:")
                            for lvl in term_levels:
                                z_type = lvl.get("zone_type", "MAJOR")
                                l_type = lvl.get("type", "LEVEL")
                                action = lvl.get("market_action", "PIVOT")
                                score = lvl.get("significance_score", 0.5)
                                mapped_price = lvl.get("price", 0.0)
                                strike = lvl.get("strike", 0.0)
                                dte = lvl.get("dte")
                                confluence = lvl.get("confluence", [])
                                zone_v2 = lvl.get("zone_type_v2", "NEUTRAL")

                                # Highlighting
                                prefix = "🔥 " if z_type == "MAJOR" else "⚡ "
                                if zone_v2 == "DEMAND_ZONE": prefix = "🟢 "
                                if zone_v2 == "SUPPLY_ZONE": prefix = "🔴 "
                                
                                action_str = f" [{action}]" if action != "PIVOT" else ""
                                conf_str = f" | [Conf: {', '.join(confluence)}]" if confluence else ""
                                dte_str = f" [DTE: {dte}]" if dte is not None else ""
                                score_str = f" (Significance: {score:.2f})"
                                
                                report.append(f"{prefix}**{mapped_price:.2f}** (Futures {strike:.2f}){action_str}{dte_str}{score_str}{conf_str}")
                else:
                    report.append("\n⚠️ No major OI liquidity zones detected for the current session/horizon.")
 
                report.append(f"\n#### 🛡️ Tactical Execution Checklist")
                at_zone = any(abs(float(l.get('price') or 0) - raw_spot) < 2.0 for l in gamma_levels) if raw_spot > 0 else False
                smc_aligned = any(l.get('confluence') for l in gamma_levels if abs(float(l.get('price') or 0) - raw_spot) < 2.0) if raw_spot > 0 else False
                at_max_pain = abs(raw_spot - max_pain) < 5.0 if raw_spot > 0 and max_pain > 0 else False

                report.append(f"- **Zone Proximity**: {'✅ PRICE AT ZONE' if at_zone else '⬜ APPROACHING'}")
                report.append(f"- **SMC Alignment**: {'✅ SMC CONFLUENCE' if smc_aligned else '⬜ WAITING'}")
                report.append(f"- **Max Pain Gravity**: {'🧲 AT ANCHOR' if at_max_pain else '⬜ CLEAR'}")
                report.append(f"- **Trend Filter**: {confirmation_info}")
                
                # Dynamic advice based on horizon
                if horizon == "short":
                    report.append(f"\n> [!TIP]\n> **Short-Term Tactical**: Focus on 0-7 DTE gamma spikes. Watch for 'pinning' near Max Pain as expiry approaches.")
                elif horizon == "long":
                    report.append(f"\n> [!NOTE]\n> **Long-Term Strategic**: These levels are institutional anchors. Use them to define major macro boundaries.")
                else:
                    report.append(f"\n> [!IMPORTANT]\n> **Execution Strategy**: Use the **Basis Adjusted Spot Levels** for your limit orders. Do not enter unless **structure shift** occurs at these levels.")

                return "\n".join(report)

            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.error(f"OI Tool Failed: {repr(e)}")
                return f"OI Tool Error: {repr(e)}"

