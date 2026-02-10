from typing import Any, Optional
import aiohttp
from app.core.config import settings
from app.core.base_tool import BaseTool

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

        if not settings.GOOGLE_CSE_ID or not settings.GOOGLE_SEARCH_API_KEY:
            return (
                f"[MOCK SEARCH RESULT for '{query}']\n"
                "Note: Real Google Search is not configured (missing GOOGLE_CSE_ID/GOOGLE_SEARCH_API_KEY).\n"
                "Simulated News:\n"
                "- Breaking: US Inflation data comes in hotter than expected (3.4% vs 3.1%).\n"
                "- Market Reaction: Gold sells off as yields spike.\n"
                "- Analyst Comment: 'Fed pivot likely delayed'."
            )
            
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": settings.GOOGLE_SEARCH_API_KEY,
            "cx": settings.GOOGLE_CSE_ID,
            "q": query,
            "num": 3
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        return f"Error searching Google: {resp.status} - {await resp.text()}"
                    
                    data = await resp.json()
                    results = []
                    for item in data.get("items", []):
                        title = item.get("title")
                        snippet = item.get("snippet")
                        link = item.get("link")
                        results.append(f"Title: {title}\nSnippet: {snippet}\nSource: {link}\n")
                        
                    if not results:
                        return "No results found."
                        
                    return "\n---\n".join(results)
            except Exception as e:
                return f"Google Search failed: {e}"
