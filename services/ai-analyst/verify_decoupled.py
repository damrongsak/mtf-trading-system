import asyncio
from app.services.sentiment import SentimentService
async def test():
    s = SentimentService()
    print(f'Result: {await s.get_sentiment("XAUUSD")}')
    await s.close()
if __name__ == "__main__":
    asyncio.run(test())