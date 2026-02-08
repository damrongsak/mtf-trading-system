from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional
import httpx
import os
import json

class SMCInput(BaseModel):
    symbol: str = Field(..., description="Symbol to analyze (e.g. XAU/USD, EUR/USD)")
    timeframe: str = Field(default="H1", description="Timeframe for analysis (e.g. H1, 15m, 4H)")

class SMCAnalystTool(BaseTool):
    name: str = "smc_technical_analysis"
    description: str = "Specific tool for Smart Money Concepts (SMC) analysis. Returns Order Blocks, FVGs, Liquidity Sweeps, and Break of Structure."
    args_schema: Type[BaseModel] = SMCInput

    def _run(self, symbol: str, timeframe: str = "H1"):
        raise NotImplementedError("Use _arun instead")

    async def _arun(self, symbol: str, timeframe: str = "H1"):
        # Map XAU/USD to XAUUSD if needed, or rely on router normalization
        # Router normalization in api-gateway might handle it, but let's be safe
        normalized_symbol = symbol.replace("/", "").replace("_", "").upper()
        if "XAU" in normalized_symbol and "USD" in normalized_symbol:
             # Try to keep standard format if possible, but api-gateway likely expects standard
             # Actually api-gateway/routers/signal.py does `symbol.upper()` and passes to `data-pipeline`.
             # `data-pipeline` uses `MarketSymbol` lookup which is flexible.
             pass

        # Use internal URL for api-gateway
        # Wait, the tool is inside ai-analyst. It should call api-gateway.
        # But api-gateway calls ai-analyst? No, circular dependency?
        # api-gateway -> ai-analyst (for /chat)
        # ai-analyst -> api-gateway (for tools)
        # This is strictly OK as long as it's not a blocking synchronous loop for the same request.
        # The user Chat request comes to API Gateway -> AI Analyst.
        # AI Analyst -> Tool -> API Gateway (/signal/latest).
        # This is a new request to API Gateway. It should be fine.
        
        # However, `api-gateway` is defined as `http://api-gateway:8000` in docker-compose?
        # Let's check docker-compose.yml.
        # `api-gateway` service name is `api-gateway`.
        
        base_url = os.getenv("API_GATEWAY_URL", "http://api-gateway:8000")
        url = f"{base_url}/api/v1/signal/latest/{symbol}"
        
        params = {"timeframe": timeframe}

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params, timeout=15.0)
                if resp.status_code != 200:
                    return f"Error fetching SMC analysis: {resp.status_code} - {resp.text}"
                
                data = resp.json().get("data")
                if not data:
                    return "No data returned for SMC analysis."
                
                # Format the output for the Analyst Persona
                analysis = data.get("analysis") or {}
                direction = data.get("direction", "NEUTRAL")
                reason = data.get("reason", "")
                price = data.get("entry_price", 0)
                
                obs = analysis.get("order_blocks", [])
                fvgs = analysis.get("fvgs", [])
                sweeps = analysis.get("liquidity_sweeps", [])
                structure = analysis.get("structure", {})
                
                # Build the report
                report = []
                report.append(f"### 🏛️ SMC Technical Analysis for {symbol} ({timeframe})")
                report.append(f"- **Current Price**: {price}")
                report.append(f"- **Signal Bias**: {direction} ({reason})")
                
                if structure:
                    trend = structure.get("trend", "Unknown")
                    bos = structure.get("last_bos", "None") # Break of Structure
                    choch = structure.get("last_choch", "None") # Change of Character
                    report.append(f"- **Market Structure**: {trend.upper()}")
                    if bos != "None": report.append(f"  - Last BOS: {bos}")
                    if choch != "None": report.append(f"  - Last CHoCH: {choch}")

                if obs:
                    report.append("\n#### 🧱 Order Blocks (OB)")
                    # Show last 3 relevant OBs
                    recent_obs = sorted(obs, key=lambda x: x.get("start_index", 0), reverse=True)[:3]
                    for ob in recent_obs:
                        mitigated = "✅ Mitigated" if ob.get("mitigated") else "⬜ Unmitigated"
                        ob_type = "Bullish" if ob.get("type") == "bullish" else "Bearish"
                        report.append(f"- **{ob_type} OB**: {ob.get('bottom')} - {ob.get('top')} ({mitigated})")
                else:
                    report.append("\n#### 🧱 Order Blocks: None detected nearby.")

                if fvgs:
                    report.append("\n#### 💧 Fair Value Gaps (FVG)")
                    recent_fvgs = sorted(fvgs, key=lambda x: x.get("start_index", 0), reverse=True)[:3]
                    for fvg in recent_fvgs:
                         mitigated = "✅ Filled" if fvg.get("mitigated") else "⬜ Open"
                         fvg_type = "Bullish" if fvg.get("type") == "bullish" else "Bearish"
                         report.append(f"- **{fvg_type} FVG**: {fvg.get('bottom')} - {fvg.get('top')} ({mitigated})")

                if sweeps:
                    report.append("\n#### 🧹 Liquidity Sweeps")
                    last_sweep = sweeps[-1] # Most recent
                    timestamp = last_sweep.get("timestamp", "Recently") # might be index or time
                    report.append(f"- **Last Sweep**: {last_sweep.get('type', '').upper()} at {last_sweep.get('price')} (Candle {last_sweep.get('index')})")
                    
                return "\n".join(report)
                
            except Exception as e:
                return f"Failed to perform SMC analysis: {str(e)}"
