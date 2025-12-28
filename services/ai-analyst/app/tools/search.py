from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional
import aiohttp
from app.core.config import settings

class SearchInput(BaseModel):
    query: str = Field(description="The query to search for (e.g., 'Why is Gold dropping?').")

class GoogleSearchTool(BaseTool):
    name: str = "google_search"
    description: str = "Searches the web for real-time information and news. Use this to find reasons for market movements."
    args_schema: Type[BaseModel] = SearchInput

    def _run(self, query: str):
        raise NotImplementedError("Use _arun instead")

    async def _arun(self, query: str):
        if not settings.GOOGLE_CSE_ID or not settings.GOOGLE_SEARCH_API_KEY:
            # Fallback / Mock behavior for demonstration
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
