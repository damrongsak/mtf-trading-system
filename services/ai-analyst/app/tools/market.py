from pydantic import BaseModel, Field
from typing import Any, Optional
import aiohttp
import json
from app.core.config import settings
from app.core.base_tool import BaseTool

class MarketContextInput(BaseModel):
    symbol: str = Field(default="XAUUSD", description="Symbol to analyze (e.g. XAUUSD)")
    count: int = Field(default=15, description="Number of recent hourly candles to fetch. Max 20 recommended to save tokens.")

class GetMarketContextTool(BaseTool):
    name: str = "get_market_context"
    description: str = "Fetches current market price, trends, and limited technical historical candles for a symbol."

    async def run(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        symbol = "XAUUSD"
        count = 15
        
        if isinstance(input_data, str) and input_data:
            try:
                data = json.loads(input_data)
                symbol = data.get("symbol", "XAUUSD")
                count = data.get("count", 15)
            except:
                symbol = input_data
        elif isinstance(input_data, dict):
            symbol = input_data.get("symbol", "XAUUSD")
            count = input_data.get("count", 15)
            
            # Robust extraction if the value itself is a dict
            if isinstance(symbol, dict):
                count = symbol.get("count", count)
                symbol = symbol.get("symbol") or "XAUUSD"
            
        async with aiohttp.ClientSession() as session:
            try:
                # Use strategy-core market/candles endpoint
                url = f"{settings.STRATEGY_CORE_URL}/api/v1/market/candles"
                params = {"symbol": symbol, "timeframe": "H1", "count": min(count, 50)} # Hard cap to prevent massive dumps
                
                async with session.get(url, params=params) as resp:
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
