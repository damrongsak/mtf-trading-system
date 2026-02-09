from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional, Any, Dict
import httpx
import os
import json
from app.core.config import settings

class MarketStateInput(BaseModel):
    symbol: str = Field(..., description="Symbol to analyze (e.g. XAU/USD, EUR/USD)")
    timeframe: str = Field(default="H1", description="Timeframe for analysis (e.g. H1, 15m, 4H)")

class MarketStateTool(BaseTool):
    name: str = "market_state_analysis"
    description: str = """Get institutional-grade market state features (The 'Sensory System').
    Provides:
    - Volatility Regime (Low, Expanding, Panic)
    - Trend Structure (Trending, Range)
    - Breakout Compression (Squeeze Detection)
    - Structural Positioning (VWAP Distance, Momentum)
    - Liquidity Condition (RVOL-based)
    - Institutional Positioning (Put/Call Ratio, Max Pain, OI Skew, Crowding Regime)
    
    Use this to understand the 'texture' and 'state' of the market before suggesting strategies or orders.
    """
    args_schema: Type[BaseModel] = MarketStateInput

    def _run(self, symbol: str, timeframe: str = "H1"):
        raise NotImplementedError("Use _arun instead")

    async def _arun(self, symbol: str, timeframe: str = "H1") -> str:
        # Normalize symbol
        normalized_symbol = symbol.replace("/", "").replace("_", "").upper()
        
        base_url = settings.API_GATEWAY_URL or "http://api-gateway:8000"
        url = f"{base_url}/api/v1/signal/market-state/{normalized_symbol}"
        params = {"timeframe": timeframe}

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params, timeout=15.0)
                if resp.status_code != 200:
                    return f"Error fetching market state: {resp.status_code} - {resp.text}"
                
                raw_data = resp.json()
                data = raw_data.get("data", {})
                
                if "error" in data:
                    return f"Market State Error: {data['error']}"

                # Format Report
                report = []
                report.append(f"### 🌐 Market State Sensory Report: {symbol} ({timeframe})")
                
                # Regimes
                report.append(f"\n#### 📊 Market Regimes")
                report.append(f"- **Volatility Regime**: `{data.get('volatility_regime', 'Unknown')}`")
                report.append(f"- **Trend Structure**: `{data.get('trend_structure', 'Unknown')}`")
                
                # Indicators
                report.append(f"\n#### 📈 Technical State")
                sq_status = "🔥 SQUEEZE DETECTED (Breakout Compression)" if data.get("is_squeeze") else "Standard Expansion"
                report.append(f"- **Compression Status**: {sq_status}")
                report.append(f"- **ADX Intensity**: {data.get('adx', 0)}")
                report.append(f"- **Momentum (10p)**: {data.get('momentum_10p_percent', 0)}%")
                
                # Value / Positioning
                report.append(f"\n#### 🎯 Structural Positioning")
                report.append(f"- **VWAP Price**: {data.get('vwap_price', 0):.2f}")
                dist = data.get('vwap_distance_percent', 0)
                report.append(f"- **Distance from Value**: {dist:.4f}% ({'Above' if dist > 0 else 'Below'} VWAP)")
                report.append(f"- **Current Rate**: {data.get('current_price', 0):.2f}")
                
                # Positioning Features (NEW)
                positioning = data.get('positioning')
                if positioning:
                    report.append(f"\n#### 🏦 Institutional Positioning (Open Interest)")
                    pcr = positioning.get('put_call_ratio', 0)
                    report.append(f"- **Put/Call Ratio**: {pcr:.3f}")
                    report.append(f"- **Crowding Regime**: `{positioning.get('crowding_regime', 'Unknown')}`")
                    report.append(f"- **Max Pain Strike**: ${positioning.get('max_pain_strike', 0):,.2f}")
                    report.append(f"- **OI Skew**: {positioning.get('skew', 0):.3f} (OTM Put/Call)")
                    report.append(f"- **Total Call OI**: {positioning.get('total_call_oi', 0):,.0f}")
                    report.append(f"- **Total Put OI**: {positioning.get('total_put_oi', 0):,.0f}")
                
                # Liquidity
                liquidity = data.get('liquidity')
                if liquidity:
                    report.append(f"\n#### 💧 Liquidity Condition")
                    report.append(f"- **Relative Volume (RVOL)**: {liquidity.get('rvol', 0):.2f}")
                    report.append(f"- **Condition**: `{liquidity.get('condition', 'Unknown')}`")
                
                # Intelligence Tip
                tip = "\n> [!TIP]\n"
                if data.get("is_squeeze"):
                    tip += "> **Squeeze Alert**: Market is in a low-volatility compression. Prepare for a high-velocity expansion/breakout."
                elif data.get("volatility_regime") == "Expanding":
                    tip += "> **Expansion Phase**: Volatility is rising. Trend-following strategies are favored, but watch for overextension from VWAP."
                elif positioning and positioning.get('crowding_regime') == 'Long Crowded':
                    tip += f"> **Long Crowding Alert**: PCR={pcr:.2f} indicates heavy bullish positioning. Watch for potential squeeze or reversal if price approaches Max Pain (${positioning.get('max_pain_strike', 0):,.0f})."
                elif positioning and positioning.get('crowding_regime') == 'Short Crowded':
                    tip += f"> **Short Crowding Alert**: PCR={pcr:.2f} indicates heavy bearish positioning. Potential short squeeze risk if price rallies."
                elif abs(dist) > 0.5:
                    tip += "> **Value Exhaustion**: Price is significantly stretched from VWAP. Mean-reversion opportunities or trailing stops should be considered."
                else:
                    tip += "> **Stable Equilibrium**: Price is oscillating near fair value. Monitor for structure breaks or session-based liquidity sweeps."
                
                report.append(tip)
                
                return "\n".join(report)
                
            except Exception as e:
                return f"Failed to perform market state analysis: {str(e)}"
