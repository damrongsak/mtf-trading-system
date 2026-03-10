import asyncio
import logging
from app.tools.market_state import MarketStateTool
from app.core.config import settings

logging.basicConfig(level=logging.INFO)

async def test_adx_tool():
    tool = MarketStateTool()
    print("--- Testing MarketStateTool (ADX) ---")
    
    # We need a mock or real auth token if required, but let's try without first
    # or use a dummy one if it expects something.
    try:
        result = await tool.arun(input_data={"symbol": "XAUUSD", "timeframe": "H1"})
        print(f"Tool Result:\n{result}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_adx_tool())
