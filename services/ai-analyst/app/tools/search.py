from typing import Any, Optional
import aiohttp
import json
import logging
from app.core.config import settings
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class GoogleSearchTool(BaseTool):
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

        # If SerpApi is configured, it takes priority (more robust results)
        if settings.SERPAPI_API_KEY:
            return await self._run_serpapi(query)

        # Fallback to Google Custom Search if configured
        if settings.GOOGLE_CSE_ID and settings.GOOGLE_SEARCH_API_KEY:
            return await self._run_google_custom_search(query)

        # Mock results if no API is configured
        return (
            f"[MOCK SEARCH RESULT for '{query}']\n"
            "Note: Real Search is not configured (missing SERPAPI_API_KEY or GOOGLE_CSE_ID).\n"
            "Simulated News:\n"
            "- Breaking: US Inflation data comes in hotter than expected (3.4% vs 3.1%).\n"
            "- Market Reaction: Gold sells off as yields spike.\n"
            "- Analyst Comment: 'Fed pivot likely delayed'."
        )

    async def _run_serpapi(self, query: str) -> str:
        url = "https://serpapi.com/search"
        params = {
            "api_key": settings.SERPAPI_API_KEY,
            "engine": "google",
            "q": query,
            "num": 3
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"SerpApi error: {resp.status} - {error_text}")
                        return f"Error searching SerpApi: {resp.status}"
                    
                    data = await resp.json()
                    results = []
                    
                    # Organic results are usually the most relevant
                    for item in data.get("organic_results", []):
                        title = item.get("title")
                        snippet = item.get("snippet")
                        link = item.get("link")
                        results.append(f"Title: {title}\nSnippet: {snippet}\nSource: {link}\n")
                        
                    if not results:
                        return "No results found on SerpApi."
                        
                    return "\n---\n".join(results)
        except Exception as e:
            logger.error(f"SerpApi execution failed: {e}")
            return f"SerpApi failed: {e}"

    async def _run_google_custom_search(self, query: str) -> str:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": settings.GOOGLE_SEARCH_API_KEY,
            "cx": settings.GOOGLE_CSE_ID,
            "q": query,
            "num": 3
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 403:
                        error_data = await resp.json()
                        err = error_data.get("error", {})
                        message = err.get("message", "Permission Denied")
                        reason = ""
                        if "details" in err:
                            reason = err["details"][0].get("reason", "")
                        
                        if reason == "API_KEY_SERVICE_BLOCKED":
                            return "Error: Google API Key restricted. Please check Cloud Console."
                        
                        return f"Google Search Access Denied: {message}"
                        
                    if resp.status != 200:
                        return f"Error searching Google: {resp.status}"
                    
                    data = await resp.json()
                    results = []
                    for item in data.get("items", []):
                        title = item.get("title")
                        snippet = item.get("snippet")
                        link = item.get("link")
                        results.append(f"Title: {title}\nSnippet: {snippet}\nSource: {link}\n")
                        
                    if not results:
                        return "No results found on Google Custom Search."
                        
                    return "\n---\n".join(results)
        except Exception as e:
            logger.error(f"Google Custom Search failed: {e}")
            return f"Google Custom Search failed: {e}"
