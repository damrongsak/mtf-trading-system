import os
import httpx
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from app.core.base_tool import BaseTool
from app.core.config import settings
from app.core.utils import parse_tool_input
import logging

logger = logging.getLogger(__name__)

class EdgeOptimizationInput(BaseModel):
    fund_id: Optional[str] = Field(None, description="Filter by Fund UUID")
    strategy_name: Optional[str] = Field(None, description="Filter by Strategy Name (e.g. 'SMC_XAU')")
    lookback_days: int = Field(30, description="Number of days to analyze")

class EdgeOptimizationTool(BaseTool):
    name: str = "get_edge_optimization"
    description: str = (
        "Analyzes historical trade data to identify the statistical 'Window of Edge'. "
        "Returns a matrix of Total PnL grouped by Entry Hour (0-23) and Day of Week (0-6). "
        "Use this to help the trader optimize their capital allocation to high-probability windows."
    )
    args_schema: Any = EdgeOptimizationInput

    async def run_tool(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        input_dict = parse_tool_input(input_data)
        
        headers = {}
        if auth_token:
            headers["Authorization"] = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"

        base_url = getattr(settings, "API_GATEWAY_URL", "http://api-gateway:8000")
        url = f"{base_url}/api/v1/analysis/metrics/edge-optimization"
        params = {
            "fund_id": input_dict.get("fund_id"),
            "strategy_name": input_dict.get("strategy_name"),
            "lookback_days": input_dict.get("lookback_days", 30)
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=headers, timeout=15.0)
                
                if response.status_code != 200:
                    return f"Error fetching Edge Optimization: {response.status_code} - {response.text}"
                
                res_json = response.json()
                data = res_json.get("data", {})
                matrix = data.get("matrix", {})
                summary = data.get("summary", {})
                
                if not matrix:
                    return f"No historical edge data found for the specified filters ({params.get('strategy_name', 'all strategies')})."

                # Days mapping
                days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
                
                report = [
                    f"### 📈 Edge Optimization Analysis (Last {params['lookback_days']} Days)",
                    f"- **Best Performance Window**: {days[summary.get('best_day', 0)]} at {summary.get('best_hour', 0):02d}:00",
                    f"- **Total PnL in Best Window**: **${summary.get('best_pnl', 0.0):.2f}**",
                    f"- **Overall Sample Size**: {summary.get('trade_count', 0)} trades",
                    f"- **Net Historical PnL**: **${summary.get('total_pnl', 0.0):.2f}**",
                    "",
                    "#### 🗓️ Day of Week Performance (Aggregate PnL)",
                ]
                
                # Group by day
                day_pnl = {d: 0.0 for d in range(7)}
                for h_str, day_data in matrix.items():
                    for d_str, pnl in day_data.items():
                        day_pnl[int(d_str)] += float(pnl)
                
                for i, day_name in enumerate(days):
                    pnl = day_pnl[i]
                    status = "✅" if pnl > 0.0 else "❌" if pnl < 0.0 else "⚪"
                    report.append(f"- **{day_name}**: {status} **${pnl:.2f}**")

                report.append("")
                report.append("> [!TIP]")
                report.append(f"> **Recommendation**: Consider increasing allocation during the **{days[summary.get('best_day', 0)]} {summary.get('best_hour', 0):02d}:00** window where your statistical edge is strongest.")

                return "\n".join(report)

        except Exception as e:
            logger.error(f"Edge Optimization Tool error: {e}")
            return f"Error generating Edge Optimization report: {str(e)}"
