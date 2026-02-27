import asyncio
import os
import sys

sys.path.append("/home/dan/workspace/mtf-trading-system/services/data-pipeline")
from app.services.news_service import NewsApiService
from app.database import SessionLocal

async def main():
    service = NewsApiService()
    
    print("--- Simulating NewsAPI Empty Response (Quota check OK, but no results) ---")
    # We will temporarily mock _fetch_from_api to return []
    original_fetch = service._fetch_from_api
    
    async def mock_fetch(symbol):
        print(f"Mocked NewsAPI call for {symbol}: Returning []")
        return []
        
    service._fetch_from_api = mock_fetch
    
    symbol = "XAUUSD"
    # First, delete the news cache
    cache_key = f"news:headlines:{symbol}"
    await service._cache_set(cache_key, None, ttl=1) # expire it
    
    print(f"Fetching headlines for {symbol}...")
    headlines = await service.fetch_headlines(symbol)
    
    print(f"Results retrieved: {len(headlines)}")
    for h in headlines[:2]:
        print(h)
        
    service._fetch_from_api = original_fetch
    # Note: we need to clean up redis connections
    
if __name__ == "__main__":
    asyncio.run(main())
