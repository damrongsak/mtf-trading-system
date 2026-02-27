from typing import Any, Optional
import aiohttp
import json
import logging
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class GoogleSearchTool(BaseTool):
    """
    Search tool standardized on SerpApi.
    Provides organic results and top stories for market context.
    """
    name: str = "google_search"
    description: str = "Searches the web for real-time information and news. Use this to find reasons for market movements."

    async def run(self, input_data: Any, auth_token: str = None, request_id: str = None) -> str:
        query = ""
        if isinstance(input_data, str):
            query = input_data
        elif isinstance(input_data, dict):
            query = input_data.get("query", "")
            
        if not query:
            return "No query provided for search."

        if not settings.SERPAPI_API_KEY:
            return (
                f"[MOCK SEARCH RESULT for '{query}']\n"
                "Note: SerpApi is not configured (missing SERPAPI_API_KEY).\n"
                "Simulated News:\n"
                "- Breaking: US Inflation data comes in hotter than expected (3.4% vs 3.1%).\n"
                "- Market Reaction: Gold sells off as yields spike.\n"
                "- Analyst Comment: 'Fed pivot likely delayed'."
            )

        # Standardized SerpApi call
        # 1. Attempt to fetch from Redis Cache first
        try:
            redis = aioredis.from_url(settings.redis.url, decode_responses=True)
            # Try matching symbols like XAUUSD
            upper_query = query.upper()
            symbol_to_check = None
            if "GOLD" in upper_query or "XAU" in upper_query:
                symbol_to_check = "XAUUSD"
            elif "EUR" in upper_query:
                symbol_to_check = "EURUSD"
            elif "BITCOIN" in upper_query or "BTC" in upper_query:
                symbol_to_check = "BTCUSD"
                
            if symbol_to_check:
                cache_key = f"market_context:{symbol_to_check}"
                cached_data = await redis.get(cache_key)
                if cached_data:
                    data = json.loads(cached_data)
                    logger.info(f"SearchTool: Cache HIT for {symbol_to_check}")
                    await redis.aclose()
                    return data.get("context", "No context found.")
            await redis.aclose()
        except Exception as e:
            logger.error(f"SearchTool Redis error: {e}")

        logger.info(f"SearchTool: Cache MISS for {query}. Falling back to SerpApi.")
        return await self._run_serpapi(query)

    async def _run_serpapi(self, query: str) -> str:
        """
        Executes search via SerpApi and returns formatted results including top_stories.
        """
        url = "https://serpapi.com/search"
        params = {
            "api_key": settings.SERPAPI_API_KEY,
            "engine": "google",
            "q": query,
            "num": 3  # Limit results per turn to save throughput and context
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=15.0, connect=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 429:
                        return "Error: SerpApi rate limit exceeded (Free plan: 50 throughput/hour)."
                    
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"SerpApi error: {resp.status} - {error_text}")
                        return f"Error searching SerpApi: {resp.status}"
                    
                    data = await resp.json()
                    results = []
                    
                    # 1. Answer Box (if available for quick facts)
                    if "answer_box" in data:
                        ab = data["answer_box"]
                        results.append(f"Direct Answer: {ab.get('answer') or ab.get('snippet')}\n")

                    # 2. Top Stories (Breaking News - High Priority)
                    if "top_stories" in data:
                        results.append(f"--- Top Stories ---")
                        for item in data.get("top_stories", [])[:3]:
                            title = item.get("title", "")
                            source = item.get("source", "")
                            date = item.get("date", "")
                            link = item.get("link", "")
                            results.append(f"News: {title}\nSource: {source} ({date})\nLink: {link}\n")

                    # 3. Organic results
                    if "organic_results" in data:
                        results.append(f"--- Search Results ---")
                        for item in data.get("organic_results", [])[:3]:
                            title = item.get("title")
                            snippet = item.get("snippet")
                            link = item.get("link")
                            results.append(f"Title: {title}\nSnippet: {snippet}\nSource: {link}\n")
                        
                    if not results:
                        return "No results found on SerpApi for this query."
                        
                    return "\n".join(results)
        except aiohttp.ServerTimeoutError:
            logger.warning(f"SerpApi timeout for query: {query[:50]}")
            return f"⚠️ Web search timed out for '{query}'. Using knowledge base as fallback."
        except Exception as e:
            logger.error(f"SerpApi execution failed: {e}")
            return f"⚠️ Web search unavailable: {type(e).__name__}. Please rely on knowledge base or market tools."
