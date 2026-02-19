import logging
import json
from typing import Any, Optional
import aiohttp
from app.core.config import settings
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class COTAnalystTool(BaseTool):
    name: str = "cot_analyst"
    description: str = """
    Fetches and interprets Commitment of Traders (COT) sentiment for Gold (XAUUSD).
    Identifies if Commercials (Hedgers) or Non-Commercials (Speculators) are bullish or bearish.
    Input JSON: {"symbol": "XAUUSD"}
    """

    async def run(self, input_data: Any = None, auth_token: str = None) -> str:
        data_pipeline_url = f"{settings.DATA_PIPELINE_URL}/api/v1"
        symbol = "GOLD" # COT uses GOLD as symbol name in our parser for XAUUSD maps
        
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
            if symbol == "XAUUSD": symbol = "GOLD"
        
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}" if not auth_token.startswith("Bearer ") else auth_token

        async with aiohttp.ClientSession() as session:
            try:
                url = f"{data_pipeline_url}/ingest/cot/latest"
                params = {"symbol": symbol}
                
                async with session.get(url, params=params, headers=headers, timeout=10.0) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if not data:
                            return "No COT data available for the requested symbol."
                        
                        # Disaggregated COT Fields mapping
                        # We use the raw values to calculate net positioning
                        nc_long = float(data.get("non_commercials_long", 0))
                        nc_short = float(data.get("non_commercials_short", 0))
                        comm_long = float(data.get("commercials_long", 0))
                        comm_short = float(data.get("commercials_short", 0))
                        
                        net_nc = nc_long - nc_short
                        net_comm = comm_long - comm_short
                        total = nc_long + nc_short + comm_long + comm_short
                        
                        nc_sentiment = "BULLISH" if net_nc > 0 else "BEARISH"
                        comm_sentiment = "BULLISH" if net_comm > 0 else "BEARISH" # Commercials usually opposite
                        
                        report = [f"### 📈 Smart Money Sentiment (COT Report: {data.get('report_date', 'N/A')})"]
                        report.append(f"\n- **Non-Commercials (Speculators)**: {nc_sentiment} (Net: {net_nc:,.0f} contracts)")
                        report.append(f"- **Commercials (Hedgers)**: {comm_sentiment} (Net: {net_comm:,.0f} contracts)")
                        
                        # Institutional Interpretation
                        bias_desc = "Neutral"
                        if nc_sentiment == "BULLISH" and net_nc > 100000:
                            bias_desc = "Strong Institutional Buying (Macro Confirmation)"
                        elif nc_sentiment == "BEARISH":
                            bias_desc = "Institutional De-risking"
                            
                        report.append(f"\n> **Strategic Bias**: {bias_desc}")
                        report.append("\nNote: Speculators (Non-Commercials) leading a trend with high net-longs is a strong trend confirmation.")
                        
                        return "\n".join(report)
                    else:
                        return f"Failed to fetch COT data ({resp.status}): {await resp.text()}"
            except Exception as e:
                logger.error(f"COT Tool Failed: {e}")
                return f"COT Tool Error: {str(e)}"
