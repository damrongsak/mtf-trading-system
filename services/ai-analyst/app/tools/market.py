from typing import Any, Optional
import aiohttp
from app.core.config import settings
from app.core.base_tool import BaseTool

class GetMarketContextTool(BaseTool):
    name: str = "get_market_context"
    description: str = "Fetches current market price, trends, and technical indicators for a symbol."

    async def run(self, input_data: Any, auth_token: str = None) -> str:
        symbol = "XAUUSD"
        if isinstance(input_data, str) and input_data:
            symbol = input_data
        elif isinstance(input_data, dict) and "symbol" in input_data:
            symbol = input_data["symbol"]
            
        async with aiohttp.ClientSession() as session:
            try:
                # Use strategy-core market/candles endpoint
                url = f"{settings.STRATEGY_CORE_URL}/api/v1/market/candles"
                params = {"symbol": symbol, "timeframe": "H1", "count": 5}
                
                async with session.get(url, params=params) as resp:
                     if resp.status == 200:
                         data = await resp.json()
                         candles = data.get("data", [])
                         summary = [
                             f"Time: {c['timestamp']}, Close: {c['close']}" for c in candles
                         ]
                         return f"Recent {symbol} Price History (H1): {summary}"
                     else:
                         return f"Error fetching market data: {resp.status}"
            except Exception as e:
                return f"Failed to connect to Strategy Core: {e}"
