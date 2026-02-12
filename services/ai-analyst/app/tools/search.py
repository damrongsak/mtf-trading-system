from typing import Any, Optional
import aiohttp
import json
import logging
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

    async def run(self, input_data: Any, auth_token: str = None) -> str:
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
        return await self._run_serpapi(query)

    async def _run_serpapi(self, query: str) -> str:
        """
        Executes search via SerpApi and returns formatted results.
        """
        url = "https://serpapi.com/search"
        params = {
            "api_key": settings.SERPAPI_API_KEY,
            "engine": "google",
            "q": query,
            "num": 3  # Limit results per turn to save throughput and context
        }
        
        try:
            async with aiohttp.ClientSession() as session:
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

                    # 2. Organic results
                    for item in data.get("organic_results", []):
                        title = item.get("title")
                        snippet = item.get("snippet")
                        link = item.get("link")
                        results.append(f"Title: {title}\nSnippet: {snippet}\nSource: {link}\n")
                        
                    if not results:
                        return "No results found on SerpApi for this query."
                        
                    return "\n---\n".join(results)
        except Exception as e:
            logger.error(f"SerpApi execution failed: {e}")
            return f"SerpApi search failed due to internal error."
