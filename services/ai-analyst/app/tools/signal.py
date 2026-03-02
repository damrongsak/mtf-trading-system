from typing import Any, Optional
import aiohttp
from app.core.config import settings
from app.core.base_tool import BaseTool

class GetTechnicalSignalsTool(BaseTool):
    name: str = "get_technical_signals"
    description: str = "Checks for active technical trading signals (SMC, Order Blocks) for a symbol."

    async def run(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        symbol = "XAUUSD"
        if isinstance(input_data, str) and input_data:
            symbol = input_data
        elif isinstance(input_data, dict) and "symbol" in input_data:
            symbol = input_data["symbol"]
            
        async with aiohttp.ClientSession() as session:
            try:
                # Call API Gateway /signal/latest/{symbol}
                url = f"{settings.API_GATEWAY_URL}/api/v1/signal/latest/{symbol}"
                
                headers = {}
                if auth_token:
                    headers["Authorization"] = auth_token

                async with session.get(url, headers=headers, timeout=3.0) as resp:
                     if resp.status == 200:
                         data = await resp.json()
                         signal_data = data.get("data", {})
                         
                         direction = signal_data.get("direction", "NEUTRAL")
                         reason = signal_data.get("reason", "No signal")
                         entry = signal_data.get("entry_price")
                         
                         return f"Signal: {direction}\nReason: {reason}\nEntry: {entry}"
                     else:
                         return f"Error fetching signals ({resp.status}): {await resp.text()}"
            except Exception as e:
                return f"Failed to connect to Signal Service: {e}"
