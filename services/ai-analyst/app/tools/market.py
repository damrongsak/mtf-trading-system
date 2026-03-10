from pydantic import BaseModel, Field
from typing import Any, Optional, Type
from app.core.base_tool import BaseTool
import aiohttp
import json
from app.core.config import settings

class MarketContextInput(BaseModel):
    symbol: str = Field(default="XAUUSD", description="Symbol to analyze (e.g. XAUUSD)")
    timeframe: str = Field(default="H1", description="Timeframe for analysis (e.g. M15, H1, H4, D1)")
    count: int = Field(default=15, description="Number of recent candles to fetch. Max 20 recommended to save tokens.")

class GetMarketContextTool(BaseTool):
    name: str = "get_market_context"
    description: str = "Fetches current market price, trends, and limited technical historical candles for a symbol on a specific timeframe."
    args_schema: Type[BaseModel] = MarketContextInput

    async def run_tool(self, input_data: Any, auth_token: str = None, request_id: str = None, **kwargs) -> str:
        symbol = "XAUUSD"
        timeframe = "H1"
        count = 15
        
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
            timeframe = input_data.get("timeframe", timeframe)
            count = input_data.get("count", count)
        elif isinstance(input_data, str):
            symbol = input_data

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
