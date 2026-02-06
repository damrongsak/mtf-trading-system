import asyncio
import sys
import os

sys.path.append(os.getcwd())

from app.services.news_service import NewsService
from app.core.config import settings
import redis.asyncio as redis

async def main():
    print("--- Verifying Enhanced News Service ---")
    
    # 1. Connect to Redis to check quota manually
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    initial_quota = await r.get(f"news_api:daily_count:{asyncio.get_event_loop().time()}") 
    # Actually key uses YYYY-MM-DD
    from datetime import datetime
    today = datetime.utcnow().strftime("%Y-%m-%d")
    key = f"news_api:daily_count:{today}"
    
    initial_count = await r.get(key)
    print(f"Initial Quota Usage: {initial_count}")
    
    # 2. Fetch Headlines (First Call)
    print("\n[1] Fetching XAU/USD (Live Call)...")
    results = await NewsService.fetch_headlines("XAU/USD")
    print(f"Result Count: {len(results)}")
    if results and "title" in results[0]:
        print(f"Sample: {results[0]['title']} ({results[0]['source']})")
    else:
        print("No results or error.")

    # 3. Check Quota Increment
    mid_count = await r.get(key)
    print(f"Quota Usage After Call 1: {mid_count}")
    
    # 4. Fetch Headlines (Second Call - Should be Cached)
    print("\n[2] Fetching XAU/USD (Cached Call)...")
    results_cached = await NewsService.fetch_headlines("XAU/USD")
    print(f"Result Count: {len(results_cached)}")
    
    # 5. Check Quota Usage (Should NOT increment)
    final_count = await r.get(key)
    print(f"Quota Usage After Call 2: {final_count}")
    
    if mid_count == final_count:
        print("\nSUCCESS: Quota did not increment for cached call.")
    else:
        print("\nWARNING: Quota incremented! Caching might be broken.")
        
    await r.close()

if __name__ == "__main__":
    asyncio.run(main())
