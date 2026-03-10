from typing import Any, Optional, Type
import aiohttp
from app.core.config import settings
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

class SignalInput(BaseModel):
    symbol: str = Field(default="XAUUSD", description="Symbol to check signals for (e.g. XAUUSD)")

class GetTechnicalSignalsTool(BaseTool):
    name: str = "get_technical_signals"
    description: str = "Checks for active technical trading trading signals (SMC, Order Blocks) for a symbol."
    args_schema: Type[BaseModel] = SignalInput

    def _run(self, symbol: str = "XAUUSD") -> str:
        import asyncio
        return asyncio.run(self._arun(symbol))

    async def _arun(self, symbol: str = "XAUUSD", auth_token: str = None, **kwargs) -> str:
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{settings.API_GATEWAY_URL}/api/v1/signal/latest/{symbol}"
                headers = {}
                if auth_token:
                    headers["Authorization"] = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"

                async with session.get(url, headers=headers, timeout=5.0) as resp:
                     if resp.status == 200:
                         data = await resp.json()
                         signal_data = data.get("data", {})
                         direction = signal_data.get("direction", "NEUTRAL")
                         reason = signal_data.get("reason", "No signal")
                         entry = signal_data.get("entry_price")
                         return f"Signal: {direction}\nReason: {reason}\nEntry: {entry}"
                     else:
                         return f"Error fetching signals: {resp.status}"
            except Exception as e:
                return f"Failed to connect to Signal Service: {str(e)}"
