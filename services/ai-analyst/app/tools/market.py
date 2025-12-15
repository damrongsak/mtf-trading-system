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
        # We'll use the /signal/check endpoint for now as it aggregates data, 
        # or we could construct a specific analysis endpoint in strategy-core.
        # Assuming strategy-core has a way to get 'latest' state.
        # If not, we might need to hit specific endpoints for price/indicators.
        # Let's try /signal/latest/{symbol} which exists in API Gateway/Strategy Core
        
        async with aiohttp.ClientSession() as session:
            # Note: strategy-core might expect slashes in symbol to be URL encoded or handled
            # typically XAU/USD -> XAUUSD or similar depending on routing. 
            # If using strategy-core directly:
            url = f"{settings.STRATEGY_CORE_URL}/api/v1/indicators/{symbol}" 
            # Wait, implementation status says /api/v1/signal/latest/{symbol} implemented in Gateway/Strategy logic
            
            # Let's assume we want raw indicators + price. 
            # For now, let's mock the return structure if endpoint is unsure, but let's try to hit a likely endpoint.
            # Strategy Core has /indicators/{symbol} mentioned in status? 
            # Status says: "Indicators: EMA, ATR, RSI... endpoints."
            
            try:
                # Fetching indicators
                async with session.get(f"{settings.STRATEGY_CORE_URL}/indicators", params={"symbol": symbol}) as resp:
                     if resp.status == 200:
                         data = await resp.json()
                         return str(data)
                     else:
                         return f"Error fetching market data: {resp.status}"
            except Exception as e:
                return f"Failed to connect to Strategy Core: {e}"
