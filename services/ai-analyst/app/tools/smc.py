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
    return_raw_data: bool = Field(default=False, description="Set to True to receive raw JSON analysis data for narrative synthesis. Use for Deep Explanation.")


class SMCAnalystTool(BaseTool):
    name: str = "smc_technical_analysis"
    description: str = "Perform institutional Smart Money Concepts (SMC) technical analysis on a specific trading symbol."
    args_schema: Type[BaseModel] = SMCInput

    async def run_tool(self, input_data: Any, auth_token: str = None, fund_id: str = None, **kwargs) -> str:
        symbol = "XAUUSD"
        timeframe = "H1"
        include_distant_zones = False
        return_raw_data = False
        
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
            timeframe = input_data.get("timeframe", timeframe)
            include_distant_zones = input_data.get("include_distant_zones", False)
            return_raw_data = input_data.get("return_raw_data", False)
        elif isinstance(input_data, str):
            # Defensive check: Is it a JSON blob passed as a string?
            if input_data.strip().startswith("{") and input_data.strip().endswith("}"):
                try:
                    parsed = json.loads(input_data)
                    symbol = parsed.get("symbol") or parsed.get("SYMBOL") or parsed.get("text", symbol)
                    timeframe = parsed.get("timeframe") or parsed.get("TIMEFRAME") or timeframe
                    return_raw_data = parsed.get("return_raw_data") or parsed.get("RETURNRAWDATA") or False
                except:
                    symbol = input_data
            else:
                symbol = input_data

        # Normalize symbol
        normalized_symbol = symbol.replace("/", "").replace("_", "").upper()
        
        from app.core.config import settings
        data_url = f"{settings.DATA_PIPELINE_URL}/api/v1/candles"
        smc_url = f"{settings.STRATEGY_CORE_URL}/api/v1/calculate/smc/mtf"
        
        headers = {}
        if auth_token:
            headers["Authorization"] = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"
        
        if fund_id:
            headers["X-Fund-ID"] = fund_id

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
                
                # 2. Prepare payload for Multi-Timeframe SMC
                payload = {
                    "symbol": normalized_symbol,
                    "timeframes": ["H4", "H1", "M15"]
                }
                if fund_id:
                    payload["fund_id"] = fund_id
                
                # 3. Call Strategy Core (MTF Endpoint)
                smc_resp = await client.post(smc_url, json=payload, headers=headers, timeout=15.0)
                if smc_resp.status_code == 200:
                    analysis_data = smc_resp.json()
                    
                    if return_raw_data:
                        return json.dumps(analysis_data)
                        
                    data = {
                        "analysis": analysis_data,
                        "direction": analysis_data.get("bias", "NEUTRAL"),
                        "reason": analysis_data.get("summary", "Consolidating."),
                        "entry_price": float(candles_data[-1]["close"]),
                        "market_status": "open",
                        "data_freshness": "real-time"
                    }
                else:
                    return f"Error from Strategy Core (MTF): {smc_resp.status_code} - {smc_resp.text}"
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
        
        checklist = analysis.get("checklist", {})
        visuals = analysis.get("visuals", {})
        confluence = analysis.get("confluence_score", 0)
        is_case_b = analysis.get("is_case_b", False)
        
        # Build the professional report
        report = [
            f"### 🏛️ Institutional SMC Briefing: {symbol}",
            f"\n> [!IMPORTANT]\n> **Market Condition**: {reason}"
        ]
        
        if is_case_b:
            report.append(f"\n> [!TIP]\n> **CASE B MITIGATION DETECTED**: Institutional liquidity has been successfully re-tested after BOS. Risk profile improved.")

        report.append(f"\n#### ⚖️ Confluence Scoring: {confluence}/6")
        
        # Checklist Table
        report.append("| Pillar | Status | Analysis |")
        report.append("| :--- | :--- | :--- |")
        for pillar, item in checklist.items():
            status_icon = "✅" if item.get("status") else "❌"
            report.append(f"| **{pillar.title()}** | {status_icon} | {item.get('comment')} |")
            
        report.append(f"\n#### 🎯 Execution Parameters")
        report.append(f"- **Institutional Bias**: {direction}")
        report.append(f"- **Trigger Level**: {visuals.get('trigger_level', 0.0):.2f}")
        report.append(f"- **Stop Loss**: {visuals.get('stop_loss', 0.0):.2f}")
        report.append(f"- **Take Profit**: {visuals.get('take_profit', 0.0):.2f}")
        
        if visuals.get("poi_zone"):
            poi = visuals["poi_zone"]
            report.append(f"- **POI Zone**: {poi.get('bottom', 0.0):.2f} - {poi.get('top', 0.0):.2f}")

        return "\n".join(report)


    def _format_age(self, seconds: int) -> str:
        if seconds < 60: return f"{seconds}s"
        elif seconds < 3600: return f"{seconds // 60}m"
        elif seconds < 86400: return f"{seconds // 3600}h"
        else: return f"{seconds // 86400}d"
