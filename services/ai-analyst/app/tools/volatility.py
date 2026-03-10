from typing import Any, Optional
import aiohttp
import logging
import json
from app.core.config import settings
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class VolatilityStructureTool(BaseTool):
    name: str = "volatility_structure_analysis"
    description: str = (
        "MANDATORY for Institutional Volatility & Structural Audit for Gold (XAUUSD). "
        "Provides Projected Implied Volatility (PIV) via GJR-GARCH/GVZ, "
        "Dynamic N-Bands (for overextension/exhaustion), and VBSR structural pivots. "
        "ALWAYS USE for M5 (Scalping), M15, H1 (Standard), or H4 (Swing) volatility context. "
        "Input: {'symbol': 'XAUUSD', 'timeframe': 'H1'}."
    )

    async def run_tool(self, input_data: Any = None, auth_token: str = None, request_id: str = None) -> str:
        symbol = "XAUUSD"
        timeframe = "H1"
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", "XAUUSD")
            timeframe = input_data.get("timeframe", "H1")

        async with aiohttp.ClientSession() as session:
            try:
                # Target Strategy Core analysis endpoint
                url = f"{settings.STRATEGY_CORE_URL}/api/v1/market/volatility/piv"
                
                headers = {}
                if auth_token:
                    headers["Authorization"] = f"Bearer {auth_token}" if not auth_token.startswith("Bearer ") else auth_token
                
                payload = {"symbol": symbol, "timeframe": timeframe, "bias": "NEUTRAL"}
                
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        proj_vol = data.get("projected_volatility", 0.0)
                        price = data.get("current_price", 0.0)
                        regime = data.get("volatility_regime", "Unknown")
                        bands = data.get("n_bands", {})
                        piv_levels = data.get("piv_levels", [])
                        
                        # Format Report
                        report = (
                            f"--- Projected Implied Volatility (PIV) Analysis: {symbol} ---\n"
                            f"- **Projected Volatility (GARCH/GVZ)**: {proj_vol:.2f} ({regime} Regime)\n"
                            f"- **Current Price**: {price:.2f}\n\n"
                            f"**N-Bands (Volatility Extremes):**\n"
                            f"  - Upper (3.0σ): {bands.get('n_band_upper_3.0', 0):.2f}\n"
                            f"  - Upper (2.0σ): {bands.get('n_band_upper_2.0', 0):.2f}\n"
                            f"  - Lower (2.0σ): {bands.get('n_band_lower_2.0', 0):.2f}\n"
                            f"  - Lower (3.0σ): {bands.get('n_band_lower_3.0', 0):.2f}\n\n"
                            f"**VBSR Structural Levels (Support/Resistance):**\n"
                            f"  {', '.join([f'{l:.2f}' for l in piv_levels[:10]])}\n\n"
                            f"**Interpretation**: "
                        )
                        
                        if price >= bands.get('n_band_upper_2.0', 999999):
                            report += "⚠️ Overextended Bullish (Mean Reversion Risk High)."
                        elif price <= bands.get('n_band_lower_2.0', 0):
                            report += "⚠️ Overextended Bearish (Mean Reversion Opportunity)."
                        else:
                            report += "Price within standard volatility bands."
                            
                        return report
                    else:
                        error_text = await resp.text()
                        logger.error(f"PIV Tool Failed ({resp.status}): {error_text}")
                        return f"PIV Analysis Unavailable: {error_text}"
            except Exception as e:
                logger.error(f"PIV Tool Exception: {e}")
                return f"Volatility Analysis Tool Error: {e}"
