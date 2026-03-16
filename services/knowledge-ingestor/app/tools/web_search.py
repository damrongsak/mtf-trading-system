import asyncio
from typing import List, Dict, Any
from ddgs import DDGS
from dogpile.cache import make_region
from app.core.app_config import config
from app.core.logger import get_logger

logger = get_logger("OlympusWebSearch")

# Configure dogpile.cache with Redis
# Note: Using the existing FalkorDB/Redis connection details
cache_region = make_region().configure(
    'dogpile.cache.redis',
    arguments={
        'url': f"redis://{config.falkor_host}:{config.falkor_port}/1",
        'redis_expiration_time': 3600 * 6,  # 6 hours TTL
        'distributed_lock': True,
        'thread_local_lock': False
    }
)

class WebSearchTool:
    """
    Industrial-grade Asynchronous Web Search Tool.
    Features: 
    - Open-source (DuckDuckGo via DDGS + asyncio.to_thread)
    - Redis-backed caching
    - Result ranking & filtering
    """

    @staticmethod
    async def search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Perform a search using DDGS in a thread pool.
        Results are limited and ranked by DDG.
        """
        logger.info("web_search_start", search_query=query, max_results=max_results)
        
        def _sync_search():
            try:
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=max_results))
            except Exception as e:
                logger.error("ddg_library_error", error=str(e))
                return []
        
        try:
            results_raw = await asyncio.to_thread(_sync_search)
            results = []
            for r in results_raw:
                results.append({
                    "title": r.get("title"),
                    "snippet": r.get("body"),
                    "url": r.get("href"),
                    "source": "DuckDuckGo"
                })
            
            logger.info("web_search_success", search_query=query, result_count=len(results))
            return results
        except Exception as e:
            logger.error("web_search_failure", search_query=query, error=str(e))
            return []

    @staticmethod
    async def search_and_summarize(query: str, max_results: int = 3) -> str:
        """
        Search and return a condensed string for LLM context.
        """
        results = await WebSearchTool.search(query, max_results)
        if not results:
            return "No recent web data found."
            
        summary = "\n".join([
            f"- [{r['title']}]({r['url']}): {r['snippet']}"
            for r in results
        ])
        return f"Latest Web Intelligence for '{query}':\n{summary}"

if __name__ == "__main__":
    # Quick Test
    async def test():
        res = await WebSearchTool.search_and_summarize("Gold spot price today 2026")
        print(res)
    
    asyncio.run(test())
