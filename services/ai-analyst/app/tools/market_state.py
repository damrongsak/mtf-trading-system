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

    async def run_tool(self, input_data: Any, auth_token: str = None, fund_id: str = None, **kwargs) -> str:
        symbol = "XAUUSD"
        timeframe = "H1"
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
            timeframe = input_data.get("timeframe", timeframe)
        elif isinstance(input_data, str):
            # Attempt to parse as JSON if it looks like a dict
            if input_data.strip().startswith("{"):
                try:
                    data = json.loads(input_data)
                    symbol = data.get("symbol", symbol)
                    timeframe = data.get("timeframe", timeframe)
                except json.JSONDecodeError:
                    symbol = input_data
            else:
                symbol = input_data

        normalized_symbol = symbol.replace("/", "").replace("_", "").upper()
        
        async with aiohttp.ClientSession() as session:
            try:
                strategy_core_url = f"{settings.STRATEGY_CORE_URL}/api/v1"
                
                headers = {}
                if auth_token:
                    headers["Authorization"] = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"
                
                # Propagate User and Fund IDs for data isolation
                user_id = kwargs.get("user_id")
                if user_id:
                    headers["X-User-Id"] = str(user_id)
                if fund_id:
                    headers["X-Fund-ID"] = str(fund_id)

                # 1 & 2. Fetch Regime and Gamma (V3.0) in parallel
                regime_url = f"{strategy_core_url}/market/regime"
                gamma_url = f"{strategy_core_url}/analysis/gamma/levels"
                
                import asyncio
                async def fetch_regime():
                    payload = {"symbol": normalized_symbol, "timeframe": timeframe}
                    if fund_id:
                        payload["fund_id"] = fund_id
                    async with session.post(regime_url, json=payload, headers=headers, timeout=10.0) as resp:
                        if resp.status == 200: 
                            return await resp.json()
                        err_text = await resp.text()
                        logger.warning(f"Regime fetch failed: {resp.status} - {err_text}")
                        return {}

                async def fetch_gamma():
                    params = {"symbol": normalized_symbol}
                    if fund_id:
                        params["fund_id"] = fund_id
                    async with session.get(gamma_url, params=params, headers=headers, timeout=10.0) as resp:
                        if resp.status == 200: 
                            return await resp.json()
                        err_text = await resp.text()
                        logger.warning(f"Gamma fetch failed: {resp.status} - {err_text}")
                        return {}

                ctx, g_ctx = await asyncio.gather(fetch_regime(), fetch_gamma())

                # 3. Process Results
                regime = ctx.get("regime", "UNSTABLE")
                score = ctx.get("regime_score", 0.0)
                risk_mult = float(ctx.get("risk_multiplier") or 1.0)
                
                # V3.0 Metrics
                g_regime = g_ctx.get("regime", {})
                lfi = float(g_regime.get("fragility_index", 0.0))
                f_alert = g_regime.get("fragility_alert", "STABLE")
                macro = g_ctx.get("macro_context") or {}
                
                is_valid = g_regime.get("is_valid", True)
                valid_status = "✅" if is_valid else "⚠️ INVALID"
                
                # Macro Logic
                macro_report = "N/A"
                if macro:
                    ry = macro.get('real_yield_10y', 'N/A')
                    dxy = macro.get('dxy_index', 'N/A')
                    macro_report = f"Real Yield: {ry}% | DXY: {dxy}"

                report = (
                    f"--- Adaptive Market State ({symbol} {timeframe}) ---\n"
                    f"- **Regime**: {regime} | Risk: {risk_mult}x\n"
                    f"- **Macro Context**: {macro_report}\n"
                    f"- **Institutional Fragility (LFI)**: `{lfi:.1f}/100` ({f_alert}) {valid_status}\n"
                    f"- **Trend Strength (ADX)**: {score:.1f}\n"
                    f"- **Gamma Profile**: {g_regime.get('regime', 'UNKNOWN')} Gamma (Flip: {g_regime.get('gamma_flip_level', 'N/A')})\n"
                    f"- **Interpretation**: The market is {regime.lower()}. "
                )
                
                if lfi > 70:
                    report += "⚠️ CAUTION: High Liquidity Fragility detected. Institutional walls are unstable."
                elif is_valid:
                    report += "Liquidity regime is stable and valid for execution."
                
                return report
                
            except Exception as e:
                logger.error(f"Failed to fetch market state: {repr(e)}", exc_info=True)
                return f"Institutional analysis tool error: {repr(e)}"

