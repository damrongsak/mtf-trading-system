import asyncio
import os
from app.tools.market_state import MarketStateTool

async def test_tool():
    tool = MarketStateTool()
    # No auth token needed for internal health check usually or we can spoof one if middleware allows
    # The tool uses settings.API_GATEWAY_URL which should be http://api-gateway:8000
    report = await tool.run(input_data={"symbol": "XAUUSD"})
    print("--- Tool Output ---")
    print(report)
    print("-------------------")

if __name__ == "__main__":
    asyncio.run(test_tool())
