import os
import httpx
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from app.core.base_tool import BaseTool
from app.core.config import settings
from app.core.utils import parse_tool_input
import logging

logger = logging.getLogger(__name__)

class RiskMapInput(BaseModel):
    symbol: str = Field(description="Trading symbol, e.g., 'XAUUSD'.")
    timeframe: str = Field(default="H1", description="Timeframe for analysis (M15, H1, H4, D1).")

class RiskMapTool(BaseTool):
    name: str = "get_risk_map"
    description: str = (
        "Fetches the institutional Quant Risk Map for a symbol. "
        "Provides a composite risk score (0-1) and breaks down Structural, Volatility, "
        "and Regime risk layers. Use this for deep risk assessment before suggesting trades."
    )
    args_schema: Any = RiskMapInput

    async def run(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        input_dict = parse_tool_input(input_data)
        symbol = input_dict.get("symbol", "XAUUSD").upper().replace("/", "").replace("_", "")
        timeframe = input_dict.get("timeframe", "H1")

        headers = {}
        if auth_token:
            headers["Authorization"] = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"

        base_url = getattr(settings, "API_GATEWAY_URL", "http://api-gateway:8000")
        url = f"{base_url}/api/v1/quant/analyze"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, 
                    json={"symbol": symbol, "timeframe": timeframe}, 
                    headers=headers, 
                    timeout=15.0
                )
                
                if response.status_code != 200:
                    return f"Error fetching Risk Map: {response.status_code} - {response.text}"
                
                data = response.json().get("data", {})
                risk_score = data.get("composite_risk_score", 0.0)
                edge_score = data.get("edge_score", 0.0)
                layers = data.get("layers", {})
                ctx = data.get("context", {})

                # Emoji-based visualization
                risk_emoji = "🟢" if risk_score < 0.4 else "🟡" if risk_score < 0.7 else "🔴"
                edge_emoji = "🔥" if edge_score > 0.8 else "✅" if edge_score > 0.6 else "⚪"

                report = [
                    f"### 📊 Institutional Risk Map: {symbol} ({timeframe})",
                    f"- **Composite Risk Score**: {risk_emoji} **{risk_score:.2f}**",
                    f"- **Edge Probabilty**: {edge_emoji} **{edge_score:.2f}**",
                    "",
                    "#### 🛡️ Layer Analysis",
                    f"- **Structural Risk**: {layers.get('structural_risk', 0.5):.2f} (SMC Demand/Supply proximity)",
                    f"- **Volatility Risk**: {layers.get('volatility_risk', 0.5):.2f} ({ctx.get('volatility_regime', 'N/A')})",
                    f"- **Regime Risk**: {layers.get('regime_risk', 0.5):.2f} ({ctx.get('regime', 'N/A')})",
                    f"- **Gamma Bias (Liquidity)**: {layers.get('gamma_bias', 'NEUTRAL')}",
                    "",
                    f"**Verdict**: {ctx.get('institutional_bias', 'NEUTRAL')} bias with {ctx.get('volatility_regime', 'stable')} volatility."
                ]
                
                return "\n".join(report)

        except Exception as e:
            logger.error(f"Risk Map Tool error: {e}")
            return f"Error generating Risk Map: {str(e)}"
