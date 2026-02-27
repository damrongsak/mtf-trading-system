import logging
import asyncio
from datetime import datetime
from typing import Dict, Any
from app.core.config import settings
from app.services.base import BaseService

logger = logging.getLogger(__name__)

class SerpApiService(BaseService):
    def __init__(self):
        super().__init__()
        self.base_url = "https://serpapi.com/search"

    async def fetch_and_cache_market_context(self, symbol: str = "XAUUSD") -> Dict[str, Any]:
        """
        Fetches market context from SerpApi, formats it, and caches in Redis.
        """
        if not settings.SERPAPI_API_KEY:
            logger.warning("SERPAPI_API_KEY is not configured.")
            return {"error": "Missing API Key"}

        query = f"latest news about {symbol} price today or market analysis"
        cache_key = f"market_context:{symbol}"

        params = {
            "api_key": settings.SERPAPI_API_KEY,
            "engine": "google",
            "q": query,
            "num": 3
        }

        try:
            session = await self.get_session()
            async with session.get(self.base_url, params=params, timeout=15.0) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"SerpApi error: {resp.status} - {error_text}")
                    return {"error": f"API Error: {resp.status}"}

                data = await resp.json()
                formatted_data = self._format_results(data, symbol)

                # Cache in Redis for 1 hour
                await self._cache_set(cache_key, formatted_data, ttl=3600)
                logger.info(f"Successfully synced market context for {symbol}")
                
                return formatted_data
                
        except asyncio.TimeoutError:
            logger.error(f"SerpApi timeout for {symbol}")
            return {"error": "Timeout"}
        except Exception as e:
            logger.error(f"SerpApi fetch failed for {symbol}: {e}")
            return {"error": str(e)}

    def _format_results(self, data: dict, symbol: str) -> dict:
        results = []
        
        # 1. Answer Box
        if "answer_box" in data:
            ab = data["answer_box"]
            results.append(f"Direct Answer: {ab.get('answer') or ab.get('snippet')}")

        # 2. Top Stories (Breaking News)
        if "top_stories" in data:
            results.append(f"--- Top Stories for {symbol} ---")
            for item in data.get("top_stories", [])[:3]:
                title = item.get("title", "")
                source = item.get("source", "")
                date = item.get("date", "")
                link = item.get("link", "")
                results.append(f"News: {title}\nSource: {source} ({date})\nLink: {link}")

        # 3. Organic Results
        if "organic_results" in data:
            results.append(f"--- Search Results for {symbol} ---")
            for item in data.get("organic_results", [])[:3]:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                results.append(f"Title: {title}\nSnippet: {snippet}\nSource: {link}")

        context_str = "\n\n".join(results)
        if not context_str:
            context_str = "No recent context found."

        return {
            "symbol": symbol,
            "context": context_str,
            "updated_at": datetime.utcnow().isoformat()
        }
