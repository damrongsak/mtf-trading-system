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

    async def run(self, input_data: Any = None, auth_token: str = None, request_id: str = None) -> str:
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

                # 4. Build the Concise Report
                raw_futures = float(underlying_futures or 0.0)
                raw_spot = float(current_price or 0.0)
                max_pain = float(g_data.get("max_pain", 0.0))
                basis = raw_futures - raw_spot if raw_futures > 0 and raw_spot > 0 else 0
                
                report = [f"**OI Snapshot ({actual_snapshot_at})**"]
                if horizon:
                    report.append(f"Horizon: {horizon.capitalize()}-Term")

                report.append(f"Spot: {raw_spot:.2f} | Futures: {raw_futures:.2f} | Max Pain: {max_pain:.2f} | Basis: {basis:+.2f}")
                
                if gamma_levels:
                    report.append("\n**Key Liquidity Zones**:")
                    # Group by term for display
                    terms = ["SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"]
                    for t in terms:
                        term_levels = [l for l in gamma_levels if l.get('term') == t]
                        if term_levels:
                            # Prune: Sort by significance score and take top 15 per term
                            term_levels = sorted(term_levels, key=lambda x: x.get("significance_score", 0), reverse=True)[:15]
                            
                            report.append(f"[{t}]")
                            for lvl in term_levels:
                                z_type = lvl.get("zone_type", "MAJOR")
                                action = lvl.get("market_action", "PIVOT")
                                score = lvl.get("significance_score", 0.5)
                                mapped_price = lvl.get("price", 0.0)
                                dte = lvl.get("dte")
                                confluence = lvl.get("confluence", [])
                                zone_v2 = lvl.get("zone_type_v2", "NEUTRAL")

                                # Concise Highlighting
                                prefix = "*" if z_type == "MAJOR" else ""
                                p_type = ""
                                if zone_v2 == "DEMAND_ZONE": p_type = " [D]"
                                elif zone_v2 == "SUPPLY_ZONE": p_type = " [S]"
                                
                                conf_str = f" | Conf: {','.join(confluence)}" if confluence else ""
                                dte_str = f" | DTE:{dte}" if dte is not None else ""
                                
                                report.append(f"- {prefix}{mapped_price:.2f}{p_type} [{action}] {dte_str} | Sig:{score:.2f}{conf_str}")
                else:
                    report.append("\nNo major OI liquidity zones detected.")
 
                report.append(f"\nExecution: {confirmation_info}")
                
                # Dynamic advice based on horizon
                if horizon == "short":
                    report.append(f"Focus: 0-7 DTE gamma spikes, pinning near Max Pain.")
                elif horizon == "long":
                    report.append(f"Focus: Institutional anchors for macro boundaries.")
                else:
                    report.append(f"Focus: Use Basis Adjusted Spot Levels. Await structure shift.")

                return "\n".join(report)

            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.error(f"OI Tool Failed: {repr(e)}")
                return f"OI Tool Error: {repr(e)}"

