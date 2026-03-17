from app.core.base_tool import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional, Any, Dict
import httpx
import os
import json
import logging

logger = logging.getLogger("ai-analyst")

class SMCInput(BaseModel):
    symbol: str = Field(default="XAUUSD", description="Symbol to analyze (e.g. XAU/USD, EUR/USD)")
    timeframe: str = Field(default="H1", description="Timeframe for analysis (e.g. H1, 15m, 4H)")
    include_distant_zones: bool = Field(default=False, description="Set to True ONLY if macro/long-term zones are explicitly needed. False by default to save tokens.")

class SMCAnalystTool(BaseTool):
    name: str = "smc_technical_analysis"
    description: str = "Perform institutional Smart Money Concepts (SMC) technical analysis on a specific trading symbol."
    args_schema: Type[BaseModel] = SMCInput

    async def run_tool(self, input_data: Any, auth_token: str = None, **kwargs) -> str:
        symbol = "XAUUSD"
        timeframe = "H1"
        include_distant_zones = False
        
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
            timeframe = input_data.get("timeframe", timeframe)
            include_distant_zones = input_data.get("include_distant_zones", False)
        elif isinstance(input_data, str):
            symbol = input_data

        # Normalize symbol
        # Normalize symbol
        normalized_symbol = symbol.replace("/", "").replace("_", "").upper()
        
        # Normalize Timeframe 
        if timeframe.lower() in ["15m", "15min", "m15"]: timeframe = "M15"
        elif timeframe.lower() in ["1h", "1hr", "h1"]: timeframe = "H1"
        elif timeframe.lower() in ["4h", "4hr", "h4"]: timeframe = "H4"
        elif timeframe.lower() in ["1d", "daily", "d1"]: timeframe = "D1"

        from app.core.config import settings
        data_url = f"{settings.DATA_PIPELINE_URL}/api/v1/candles"
        smc_url = f"{settings.STRATEGY_CORE_URL}/api/v1/calculate/smc"
        
        headers = {}
        if auth_token:
            headers["Authorization"] = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"

        data = None
        # 1. Fetch Candles from Data Pipeline
        async with httpx.AsyncClient() as client:
            try:
                # Fetch 100 candles
                candles_resp = await client.get(data_url, params={"symbol": normalized_symbol, "timeframe": timeframe, "page_size": 100}, headers=headers, timeout=5.0)
                if candles_resp.status_code != 200:
                    return f"Error fetching candles from Data Pipeline: {candles_resp.status_code}"
                
                candles_data = candles_resp.json().get("data", [])
                if not candles_data:
                    return f"No candle data available for {normalized_symbol} on {timeframe}."
                
                # Reverse to ascending order for analysis
                candles_data.reverse()
                
                # 2. Prepare payload for Strategy Core
                payload = {
                    "symbol": normalized_symbol,
                    "timeframe": timeframe,
                    "open": [float(c["open"]) for c in candles_data],
                    "high": [float(c["high"]) for c in candles_data],
                    "low": [float(c["low"]) for c in candles_data],
                    "close": [float(c["close"]) for c in candles_data],
                    "volume": [float(c["volume"]) for c in candles_data],
                    "timestamps": [c["timestamp"] for c in candles_data]
                }
                
                # 3. Call Strategy Core
                smc_resp = await client.post(smc_url, json=payload, headers=headers, timeout=10.0)
                if smc_resp.status_code == 200:
                    # Enrich with market status metadata (Simplified version for AI)
                    analysis_data = smc_resp.json()
                    data = {
                        "analysis": analysis_data,
                        "direction": analysis_data.get("institutional_bias", "NEUTRAL"),
                        "reason": analysis_data.get("strategic_reasoning", "Consolidating."),
                        "entry_price": float(candles_data[-1]["close"]),
                        "market_status": "open", # Assumed if we have recent candles
                        "data_freshness": "real-time"
                    }
                else:
                    return f"Error from Strategy Core: {smc_resp.status_code} - {smc_resp.text}"
            except Exception as e:
                return f"Internal Orchestration Error in SMC Tool: {str(e)}"
                
        # 3. Process data
        market_status = data.get("market_status", "unknown")
        market_reason = data.get("market_reason", "")
        data_age = data.get("data_age_seconds", 0)
        freshness = data.get("data_freshness", "unknown")
        
        # Extract analysis data
        analysis = data.get("analysis") or {}
        direction = data.get("direction", "NEUTRAL")
        reason = data.get("reason", "Consolidating at structural levels.")
        price = data.get("entry_price", 0)
        current_price_val = float(price or 0.0)
        
        global_meta = analysis.get("meta", {})
        
        # --- Dynamic Volatility Filtering ---
        atr_baseline = float(global_meta.get("atr", current_price_val * 0.005) or current_price_val * 0.005)
        max_range = atr_baseline * 3.0
        upper_bound = current_price_val + max_range
        lower_bound = current_price_val - max_range

        def is_in_range(top, bottom):
            if include_distant_zones: return True
            if current_price_val == 0: return True
            return not (bottom > upper_bound or top < lower_bound)

        raw_obs = analysis.get("order_blocks", [])
        raw_fvgs = analysis.get("fvgs", [])
        
        obs = [ob for ob in raw_obs if is_in_range(float(ob.get('top') or 0), float(ob.get('bottom') or 0))]
        fvgs = [fvg for fvg in raw_fvgs if is_in_range(float(fvg.get('top') or 0), float(fvg.get('bottom') or 0))]
        
        filtered_out = (len(raw_obs) - len(obs)) + (len(raw_fvgs) - len(fvgs))
        structure = analysis.get("structure", {})
        
        # Build the professional report
        report = [
            f"### 🏛️ SMC Institutional Analysis: {symbol} ({timeframe})",
            f"\n> **📊 Data Source:** Real-time database feed from active broker connection"
        ]
        
        if not include_distant_zones and filtered_out > 0:
           report.append(f"> **✂️ Relevance Filter ACTIVE:** {filtered_out} distant zones hidden. Range: {lower_bound:.2f} to {upper_bound:.2f} (+/- 3x ATR).")

        if market_status == "closed":
            report.append(f"\n> [!NOTE]\n> **📊 Analysis Mode**: Historical Data Analysis\n> Markets are currently closed ({market_reason}).")
        
        report.append(f"\n- **Current Rate**: {current_price_val:.2f}")
        report.append(f"- **Institutional Bias**: {direction}")
        report.append(f"- **Strategic Assessment**: {reason}")
        
        vol = float(global_meta.get("volatility_score") or 0.0)
        report.append(f"- **Volatility Environment**: {'High' if vol > 0.005 else 'Contracting'} (Index: {vol:.4f})")

        if obs:
            report.append("\n#### 🧱 Institutional Order Blocks (OB)")
            for ob in sorted(obs, key=lambda x: x.get("index", 0), reverse=True)[:3]:
                mitigated = "✅ Mitigated" if ob.get("mitigated") else "⬜ FRESH"
                report.append(f"- **{ob.get('type').capitalize()}**: {float(ob.get('bottom')):.2f} - {float(ob.get('top')):.2f} [{mitigated}]")
        
        if fvgs:
            report.append("\n#### 💧 Liquidity Gaps (FVG)")
            for fvg in sorted(fvgs, key=lambda x: x.get("index", 0), reverse=True)[:2]:
                report.append(f"- **{fvg.get('type').capitalize()}**: {float(fvg.get('bottom')):.2f} - {float(fvg.get('top')):.2f}")

        return "\n".join(report)

    def _format_age(self, seconds: int) -> str:
        if seconds < 60: return f"{seconds}s"
        elif seconds < 3600: return f"{seconds // 60}m"
        elif seconds < 86400: return f"{seconds // 3600}h"
        else: return f"{seconds // 86400}d"
