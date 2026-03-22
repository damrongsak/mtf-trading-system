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

    async def run_tool(self, input_data: Any, auth_token: str = None, request_id: str = None, **kwargs) -> Any:
        symbol = "XAUUSD"
        timeframe = "H1"
        count = 15
        
        if isinstance(input_data, dict):
            symbol = input_data.get("symbol", symbol)
            timeframe = input_data.get("timeframe", timeframe)
            count = input_data.get("count", count)
        elif isinstance(input_data, str):
            # Defensive JSON check
            if input_data.strip().startswith("{") and input_data.strip().endswith("}"):
                try:
                    parsed = json.loads(input_data)
                    symbol = parsed.get("symbol") or parsed.get("SYMBOL") or symbol
                    timeframe = parsed.get("timeframe") or parsed.get("TIMEFRAME") or timeframe
                except:
                    symbol = input_data
            else:
                symbol = input_data

        # Normalize symbol
        normalized_symbol = symbol.replace("/", "").replace("_", "").upper()


        async with aiohttp.ClientSession() as session:
            try:
                # Use strategy-core market/candles endpoint
                url = f"{settings.STRATEGY_CORE_URL}/api/v1/market/candles"
                params = {"symbol": normalized_symbol, "timeframe": timeframe, "count": min(count, 50)}
                
                headers = {}
                if auth_token:
                    headers["Authorization"] = f"Bearer {auth_token}" if not auth_token.startswith("Bearer ") else auth_token

                async with session.get(url, params=params, headers=headers, timeout=3.0) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        candles = data.get("data", [])
                        
                        from app.utils.distiller import DataDistiller
                        distilled = DataDistiller.distill_candles(candles, count=10)
                        
                        # Return structured data for the graph + string for the LLM
                        return {
                            "distilled": distilled,
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "volatility": "unknown", # Heuristic if not provided by strategy-core
                            "trend_bias": "neutral",
                            "raw_count": len(candles)
                        }
                    else:
                        return {"error": f"Error fetching market data: {resp.status}"}
            except Exception as e:
                return {"error": f"Failed to connect to Strategy Core: {e}"}
