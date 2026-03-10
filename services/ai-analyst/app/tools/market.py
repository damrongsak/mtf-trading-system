from pydantic import BaseModel, Field
from typing import Any, Optional, Type
from langchain_core.tools import BaseTool as LCTool
import aiohttp
import json
from app.core.config import settings

class MarketContextInput(BaseModel):
    symbol: str = Field(default="XAUUSD", description="Symbol to analyze (e.g. XAUUSD)")
    timeframe: str = Field(default="H1", description="Timeframe for analysis (e.g. M15, H1, H4, D1)")
    count: int = Field(default=15, description="Number of recent candles to fetch. Max 20 recommended to save tokens.")

class GetMarketContextTool(LCTool):
    name: str = "get_market_context"
    description: str = "Fetches current market price, trends, and limited technical historical candles for a symbol on a specific timeframe."
    args_schema: Type[BaseModel] = MarketContextInput

    def _run(self, symbol: str = "XAUUSD", timeframe: str = "H1", count: int = 15) -> str:
        import asyncio
        return asyncio.run(self._arun(symbol, timeframe, count))

    async def _arun(self, symbol: str = "XAUUSD", timeframe: str = "H1", count: int = 15, auth_token: str = None, request_id: str = None) -> str:
        async with aiohttp.ClientSession() as session:
            try:
                # Use strategy-core market/candles endpoint
                url = f"{settings.STRATEGY_CORE_URL}/api/v1/market/candles"
                params = {"symbol": symbol, "timeframe": timeframe, "count": min(count, 50)} # Hard cap to prevent massive dumps
                
                async with session.get(url, params=params, timeout=3.0) as resp:
                     if resp.status == 200:
                          data = await resp.json()
                          candles = data.get("data", [])
                          
                          from app.utils.distiller import DataDistiller
                          distilled = DataDistiller.distill_candles(candles, count=10)
                          return f"Distilled Market Context for {symbol}: {distilled}"
                     else:
                         return f"Error fetching market data: {resp.status}"
            except Exception as e:
                return f"Failed to connect to Strategy Core: {e}"
