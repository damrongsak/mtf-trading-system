import json
import logging
import httpx
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.base_tool import BaseTool
from app.core.config import settings

logger = logging.getLogger(__name__)

class IndicatorSpec(BaseModel):
    type: str = Field(
        ..., 
        description="Supported values: 'atr', 'rsi', 'ema', 'macd'"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Custom parameters for the indicator. If omitted, institutional defaults are used. "
            "Supported parameters:\n"
            "- atr: { 'window': int (default 14) }\n"
            "- rsi: { 'window': int (default 14) }\n"
            "- ema: { 'span': int (default 200) }\n"
            "- macd: { 'fast': int (default 12), 'slow': int (default 26), 'signal': int (default 9) }"
        )
    )

class TechnicalIndicatorsInput(BaseModel):
    symbol: str = Field(
        default="XAUUSD", 
        description="The trading symbol to analyze. Must follow ISO 4217 standard (e.g. XAUUSD). Default: XAUUSD."
    )
    timeframe: str = Field(
        default="H1", 
        description="The data resolution timeframe. Supported: M1, M5, M15, H1, H4, D1, W1, MN1."
    )
    indicators: List[IndicatorSpec] = Field(
        default_factory=lambda: [
            IndicatorSpec(type="atr", params={"window": 14}),
            IndicatorSpec(type="rsi", params={"window": 14}),
            IndicatorSpec(type="ema", params={"span": 20}),
            IndicatorSpec(type="macd", params={"fast": 12, "slow": 26, "signal": 9})
        ],
        description="A list of indicators to calculate simultaneously. Defaults to ATR, RSI, EMA, and MACD."
    )

class TechnicalIndicatorsTool(BaseTool):
    name: str = "get_technical_indicators"
    description: str = (
        "Batch calculates institutional-grade technical indicators (ATR, RSI, EMA, MACD) in a single request. "
        "Allows dynamic specification of indicator parameters (e.g., custom window sizes). "
        "Use this tool to evaluate momentum, volatility, support/resistance, and trend characteristics simultaneously. "
        "Returns 'White-Box' analysis including calculated values, bias, strength, and expert interpretations."
    )
    args_schema: type[BaseModel] = TechnicalIndicatorsInput

    async def run_tool(self, input_data: Any, auth_token: str = None, request_id: str = None, **kwargs) -> str:
        # Prevent circular logic/unauthenticated issues by mandating tokens if required by Gateway.
        headers = {}
        if auth_token:
            headers["Authorization"] = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"
            
        # Propagate User and Fund IDs for data isolation
        user_id = kwargs.get("user_id")
        fund_id = kwargs.get("fund_id")
        if user_id:
            headers["X-User-ID"] = str(user_id)
        if fund_id:
            headers["X-Fund-ID"] = str(fund_id)

        # Call Strategy Core directly (No Reentrancy)
        base_url = settings.STRATEGY_CORE_URL
        url = f"{base_url}/api/v1/indicators"
        
        # Determine payload
        payload = {}
        if isinstance(input_data, str):
            try:
                payload = json.loads(input_data)
            except Exception as e:
                return f"Error: Failed to parse input JSON. Make sure you pass valid JSON matching the schema. ({e})"
        elif isinstance(input_data, dict):
            payload = input_data
        elif isinstance(input_data, TechnicalIndicatorsInput):
            payload = input_data.model_dump()
        else:
            return "Error: Invalid input format."

        # Inject fund_id from ContextVar
        from app.utils.tracing import fund_id_ctx
        f_id = fund_id_ctx.get(None)
        if f_id and not payload.get("fund_id"):
            payload["fund_id"] = f_id

        # Make request to the Universal Indicator Engine
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=25.0 # Initial Numba compile can take ~10-15s
                )
                
                if response.status_code != 200:
                    return f"Indicator Engine Error ({response.status_code}): {response.text}"
                
                data = response.json()
                results = data.get("results", {})
                
                # Format into a clean, markdown-friendly string for the LLM
                report = [
                    f"### 🎛️ Technical Indicators for {payload.get('symbol')} ({payload.get('timeframe')})",
                    "---"
                ]
                
                for ind_name, ind_data in results.items():
                    error = ind_data.get("error")
                    if error:
                        report.append(f"**{ind_name.upper()}**: ❌ Error - {error}")
                        continue
                    
                    interpretation = ind_data.get("interpretation", {})
                    meta = ind_data.get("meta", {})
                    
                    summary = interpretation.get("summary", "No summary.")
                    bias = interpretation.get("bias", "NEUTRAL")
                    strength = interpretation.get("strength", 0.0)
                    ai_advice = interpretation.get("ai_advice", "")
                    
                    # Identify configuration used
                    params = meta.get("parameters", {})
                    params_str = ", ".join([f"{k}={v}" for k, v in params.items()])
                    config_str = f"({params_str})" if params_str else "(Default)"

                    report.append(f"#### {ind_name.upper()} {config_str}")
                    report.append(f"- **Bias**: {bias} (Strength: {strength:.2f})")
                    report.append(f"- **Summary**: {summary}")
                    if ai_advice:
                        report.append(f"- **AI Advice**: {ai_advice}")
                    report.append("") # Empty line for spacing
                    
                report.append(f"*Latency: {data.get('batch_latency_ms', 0):.2f}ms | Source: {data.get('data_source', 'Unknown')}*")
                
                return "\n".join(report)

        except httpx.ReadTimeout:
            return "Error: Indicator Engine timed out. (This might happen on the first request due to JIT compilation. Please retry.)"
        except Exception as e:
            logger.error(f"TechnicalIndicatorsTool Error: {e}")
            return f"Error executing TechnicalIndicatorsTool: {str(e)}"
