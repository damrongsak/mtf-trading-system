import asyncio
import os
import sys
import aiohttp
import json

sys.path.append("/home/dan/workspace/mtf-trading-system/services/ai-analyst")
from app.core.config import settings

async def main():
    url = "https://serpapi.com/search"
    query = "latest news about gold price today"
    params = {
        "api_key": settings.SERPAPI_API_KEY,
        "engine": "google",
        "q": query,
        "num": 3
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            # print top level keys
            print("Keys:", list(data.keys()))
            if "top_stories" in data:
                print("Top Stories:", json.dumps(data["top_stories"], indent=2))
            if "news_results" in data:
                print("News Results:", json.dumps(data["news_results"], indent=2))

if __name__ == "__main__":
    asyncio.run(main())
