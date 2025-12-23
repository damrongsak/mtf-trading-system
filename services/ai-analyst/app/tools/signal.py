from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Type
import aiohttp
from app.core.config import settings

class SignalInput(BaseModel):
    symbol: str = Field(description="The trading symbol to check signals for, e.g., 'XAU/USD'")

class GetTechnicalSignalsTool(BaseTool):
    name: str = "get_technical_signals"
    description: str = "Checks for active technical trading signals (SMC, Order Blocks) for a symbol."
    args_schema: Type[BaseModel] = SignalInput

    def _run(self, symbol: str):
        raise NotImplementedError("Use _arun instead")

    async def _arun(self, symbol: str):
        async with aiohttp.ClientSession() as session:
            try:
                # Call API Gateway /signal/latest/{symbol}
                # Handles internally: Data fetching -> Strategy Core Analysis -> Logic
                url = f"{settings.API_GATEWAY_URL}/api/v1/signal/latest/{symbol}"
                # URL encode symbol just in case, but usually requests handles it, or path param
                # Requests/aiohttp might not auto-encode path params if manually constructed string.
                # XAU/USD -> XAU%2FUSD or XAU_USD? API Gateway expects path. 
                # signal.py uses {symbol:path} so slashes are allowed.
                
                async with session.get(url) as resp:
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
