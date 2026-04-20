from typing import Any, Optional, Type, List
import aiohttp
import logging
import json
from app.core.config import settings
from app.core.base_tool import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class MarketStateInput(BaseModel):
    symbol: str = Field(default="XAUUSD", description="Symbol to fetch market state for.")
    timeframe: str = Field(default="H1", description="Anchor timeframe for state analysis (M15, H1, H4, D1).")

class MarketStateTool(BaseTool):
    name: str = "market_state"
    description: str = "Fetches comprehensive institutional market state including PCR, Max Pain, and Volatility projected from strategy-core."
    args_schema: Type[BaseModel] = MarketStateInput

    async def run_tool(self, input_data: Any, auth_token: str = None, **kwargs) -> str:
        symbol = "XAUUSD"
        timeframe = "H1"
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
            timeframe = input_data.get("timeframe", timeframe)
        elif isinstance(input_data, str):
            # Defensive JSON check
            if input_data.strip().startswith("{") and input_data.strip().endswith("}"):
                try:
                    parsed = json.loads(input_data)
                    symbol = parsed.get("symbol") or parsed.get("SYMBOL") or symbol
                    timeframe = parsed.get("timeframe") or parsed.get("TIMEFRAME") or timeframe
                except:
                    symbol = input_data
            else:
                symbol = input_data

        # Normalize symbol
        normalized_symbol = symbol.replace("/", "").replace("_", "").upper()
        
        async with aiohttp.ClientSession() as session:
            try:
                # We use direct service URLs instead of API Gateway
                strategy_core_url = f"{settings.STRATEGY_CORE_URL}/api/v1"
                
                headers = {}
                if auth_token:
                    if not auth_token.startswith("Bearer "):
                        headers["Authorization"] = f"Bearer {auth_token}"
                    else:
                        headers["Authorization"] = auth_token
                
                # 1 & 2. Fetch Regime and Gamma in parallel with strict 3s target
                logger.info(f"MarketState: Fetching parallel data for {normalized_symbol}")
                regime_url = f"{strategy_core_url}/market/regime"
                gamma_url = f"{strategy_core_url}/analysis/gamma/levels"
                
                regime_payload = {"symbol": normalized_symbol, "timeframe": timeframe, "bias": "NEUTRAL"}
                
                import asyncio
                
                async def fetch_regime():
                    async with session.post(regime_url, json=regime_payload, headers=headers, timeout=2.5) as resp:
                        if resp.status == 200: return await resp.json()
                        return {}

                async def fetch_gamma():
                    async with session.get(gamma_url, params={"symbol": normalized_symbol}, headers=headers, timeout=2.5) as resp:
                        if resp.status == 200: return await resp.json()
                        return {}

                
                try:
                    regime_task = fetch_regime()
                    gamma_task = fetch_gamma()
                    ctx, g_ctx = await asyncio.gather(regime_task, gamma_task)
                except Exception as e:
                    logger.warning(f"MarketState parallel fetch failed: {e}")
                    ctx, g_ctx = {}, {}

                # 3. Process Results
                regime = ctx.get("regime", "UNSTABLE")
                score = ctx.get("regime_score", 0.0)
                fakeout = ctx.get("fakeout_type")
                
                try:
                    risk_mult = float(ctx.get("risk_multiplier") or ctx.get("recommended_risk") or 1.0)
                except (TypeError, ValueError):
                    risk_mult = 1.0
                
                fakeout_text = "None"
                if fakeout:
                    fakeout_text = f"⚠️ {fakeout} (Trap Detected)"
                
                risk_advice = "STANDARD"
                if risk_mult < 1.0: risk_advice = "REDUCED SIZE (CAUTION)"
                elif risk_mult > 1.0: risk_advice = "AGGRESSIVE (HIGH PROB)"
                
                gamma_report = "Unavailable"
                if g_ctx:
                    if "error" in g_ctx:
                        gamma_report = g_ctx["error"]
                    else:
                        g_regime = g_ctx.get("regime", {})
                        g_levels = g_ctx.get("levels", [])
                        call_wall = next((l for l in g_levels if l.get("type") == "CALL_WALL"), None)
                        put_wall = next((l for l in g_levels if l.get("type") == "PUT_WALL"), None)
                        
                        is_valid = g_regime.get("is_valid", True)
                        alerts = g_regime.get("integrity_alerts", [])
                        valid_status = "✅" if is_valid else f"⚠️ INVALID ({', '.join(alerts)})"
                        
                        gamma_report = (
                            f"**{g_regime.get('regime', 'UNKNOWN')} Gamma** {valid_status}\n"
                            f"  - Gamma Flip: {g_regime.get('gamma_flip_level', 'N/A')}\n"
                            f"  - Call Wall: {call_wall['strike'] if call_wall else 'N/A'}\n"
                            f"  - Put Wall: {put_wall['strike'] if put_wall else 'N/A'}"
                        )
                adx_slope = float(ctx.get("adx_slope", 0.0))
                p_di = float(ctx.get("plus_di", 0.0))
                m_di = float(ctx.get("minus_di", 0.0))
                
                slope_text = "Steady"
                if adx_slope > 1.5: slope_text = "Strengthening 📈"
                elif adx_slope < -1.5: slope_text = "Weakening 📉"
                
                di_text = "Neutral"
                if p_di > m_di + 5: di_text = "Bullish Dominance (DI+ > DI-)"
                elif m_di > p_di + 5: di_text = "Bearish Dominance (DI- > DI+)"
                
                report = (
                    f"--- Adaptive Market State ({symbol} {timeframe}) ---\n"
                    f"- Regime: {regime}\n"
                    f"- **Trend Strength (ADX)**: {score:.1f} ({slope_text})\n"
                    f"- **Directional Index**: {di_text} [+DI: {p_di:.1f}, -DI: {m_di:.1f}]\n"
                    f"- Fakeout/Trap: {fakeout_text}\n"
                    f"- **Dynamic Risk**: {risk_mult}x ({risk_advice})\n"
                    f"- **Liquidity Profile (Gamma)**: {gamma_report}\n"
                    f"- Context: The market is {regime.split('_')[0].lower()} with {fakeout_text.lower() if fakeout else 'no'} traps."
                )
                return report
            except Exception as e:
                logger.error(f"Failed to fetch market state: {e}")
                return f"Institutional analysis tool error: {e}"
