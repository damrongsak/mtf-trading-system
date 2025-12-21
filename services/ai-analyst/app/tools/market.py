from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Type
import aiohttp
from app.core.config import settings

class MarketContextInput(BaseModel):
    symbol: str = Field(description="The trading symbol to analyze, e.g., 'XAU/USD'")

class GetMarketContextTool(BaseTool):
    name: str = "get_market_context"
    description: str = "Fetches current market price, trends, and technical indicators for a symbol."
    args_schema: Type[BaseModel] = MarketContextInput

    def _run(self, symbol: str):
        raise NotImplementedError("Use _arun instead")

    async def _arun(self, symbol: str):
        async with aiohttp.ClientSession() as session:
            try:
                # Use strategy-core market/candles endpoint
                url = f"{settings.STRATEGY_CORE_URL}/api/v1/market/candles"
                params = {"symbol": symbol, "timeframe": "H1", "count": 5}
                
                async with session.get(url, params=params) as resp:
                     if resp.status == 200:
                         data = await resp.json()
                         # Simplify data for LLM
                         candles = data.get("data", [])
                         summary = [
                             f"Time: {c['time']}, Close: {c['close']}" for c in candles
                         ]
                         return f"Recent {symbol} Price History (H1): {summary}"
                     else:
                         return f"Error fetching market data: {resp.status}"
            except Exception as e:
                return f"Failed to connect to Strategy Core: {e}"
