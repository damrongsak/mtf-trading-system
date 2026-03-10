
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.tools.heatmap import LiquidityHeatmapTool

async def test_heatmap_signature():
    print("--- Testing LiquidityHeatmapTool Signature ---")
    tool = LiquidityHeatmapTool()
    
    # Simulate diagnostic input
    exec_input = {"symbol": "XAUUSD", "auth_token": "fake_token"}
    
    # We want to see if calling arun(exec_input) results in the TypeError
    # Mocking Redis and aiohttp to avoid real IO
    with patch("redis.asyncio.from_url") as mock_redis_cls:
        mock_redis = AsyncMock()
        mock_redis_cls.return_value = mock_redis
        
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json.return_value = {"heatmap": [], "max_pain": 0, "underlying_price": 2000}
            mock_get.return_value.__aenter__.return_value = mock_resp
            
            try:
                # Call arun which goes through BaseTool logic
                result = await tool.arun(exec_input)
                print(f"Result: {result}")
            except Exception as e:
                print(f"Caught Exception in test: {repr(e)}")

# Mocking the BaseTool dependencies if needed
if __name__ == "__main__":
    asyncio.run(test_heatmap_signature())
