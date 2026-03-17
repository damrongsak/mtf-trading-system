from typing import Any, Optional, Type
import httpx
from app.core.config import settings
from app.core.base_tool import BaseTool
from pydantic import BaseModel, Field

class SignalInput(BaseModel):
    symbol: str = Field(default="XAUUSD", description="Symbol to check signals for (e.g. XAUUSD)")

class GetTechnicalSignalsTool(BaseTool):
    name: str = "get_technical_signals"
    description: str = "Checks for active technical trading trading signals (SMC, Order Blocks) for a symbol."
    args_schema: Type[BaseModel] = SignalInput

    async def run_tool(self, input_data: Any, auth_token: str = None, **kwargs) -> str:
        symbol = "XAUUSD"
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
        elif isinstance(input_data, str):
            symbol = input_data

        # 2. Direct Orchestration (Avoid Gateway Deadlock)
        headers = {}
        if auth_token:
            headers["Authorization"] = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"

        async with httpx.AsyncClient() as client:
            try:
                # 1. Fetch Candles
                candles_resp = await client.get(
                    f"{settings.DATA_PIPELINE_URL}/api/v1/candles", 
                    params={"symbol": symbol, "timeframe": "H1", "page_size": 100},
                    headers=headers,
                    timeout=10.0
                )
                if candles_resp.status_code != 200:
                    return f"Error fetching candles: {candles_resp.status_code}"
                
                candles = candles_resp.json().get("data", [])
                if not candles:
                    return "No signal data available (no candles found in pipeline)."
                
                # 2. Analyze with Strategy Core
                candles.reverse() # Ascending order
                smc_payload = {
                    "symbol": symbol,
                    "timeframe": "H1",
                    "open": [float(c["open"]) for c in candles],
                    "high": [float(c["high"]) for c in candles],
                    "low": [float(c["low"]) for c in candles],
                    "close": [float(c["close"]) for c in candles],
                    "volume": [float(c["volume"]) for c in candles],
                    "timestamps": [c["timestamp"] for c in candles]
                }
                smc_resp = await client.post(
                    f"{settings.STRATEGY_CORE_URL}/api/v1/calculate/smc",
                    json=smc_payload,
                    headers=headers,
                    timeout=15.0
                )
                
                if smc_resp.status_code == 200:
                    analysis = smc_resp.json()
                    direction = analysis.get("institutional_bias", "NEUTRAL")
                    reason = analysis.get("strategic_reasoning", "No signal")
                    entry = candles[-1]["close"]
                    return f"Signal: {direction}\nReason: {reason}\nEntry: {entry}"
                else:
                    return f"Error from Strategy Service: {smc_resp.status_code} - {smc_resp.text}"
            except Exception as e:
                return f"Failed to connect to internal services: {str(e)}"
