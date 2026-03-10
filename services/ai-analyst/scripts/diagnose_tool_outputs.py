
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.tools.market import GetMarketContextTool
from app.tools.strategy import StrategyBacktestTool
from app.tools.calendar import GetEconomicCalendarTool
from app.tools.account import GetAccountStatusTool
from app.tools.search import GoogleSearchTool

async def diagnose_tools():
    print("--- Diagnosing GetEconomicCalendarTool ---")
    tool = GetEconomicCalendarTool()
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"datetime": "2024-01-01T10:00:00Z", "country": "USD", "impact": "High", "title": "NFP", "forecast": "200k"}
        ]
        mock_get.return_value = mock_resp
        result = await tool.arun("USD")
        print(f"Result: {result}")

    print("\n--- Diagnosing GetAccountStatusTool ---")
    tool = GetAccountStatusTool()
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = {
            "status": "success",
            "data": {
                "balance": "10000.00 USDT",
                "equity": "10500.50",
                "marginAvailable": "10000.50", 
                "open_positions": [{"symbol": "XAU/USD", "pnl": 50.0, "risk_usd": 10.0}]
            }
        }
        mock_get.return_value.__aenter__.return_value = mock_resp
        result = await tool.arun({}, auth_token="fake")
        print(f"Result: {result}")

    print("\n--- Diagnosing GoogleSearchTool ---")
    tool = GoogleSearchTool()
    # Mock Redis to miss
    with patch("redis.asyncio.from_url") as mock_redis_cls:
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis_cls.return_value = mock_redis
        
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json.return_value = {
                "data": [{"title": "Gold up $50", "source": "Bloomberg", "published_at": "2024-03-10"}]
            }
            mock_get.return_value.__aenter__.return_value = mock_resp
            result = await tool.arun("XAUUSD")
            print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(diagnose_tools())
