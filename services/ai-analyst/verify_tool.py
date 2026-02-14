import asyncio
from app.tools.market_state import MarketStateTool

async def main():
    tool = MarketStateTool()
    print("Running MarketStateTool...")
    result = await tool.run(input_data={'symbol': 'XAUUSD', 'timeframe': 'H1'})
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
