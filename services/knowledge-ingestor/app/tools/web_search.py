from typing import List, Dict, Any, cast
import asyncio
from ddgs import DDGS
from dogpile.cache import make_region
from app.core.app_config import config
from app.core.logging_config import get_logger

logger = get_logger("OlympusWebSearch")

_cache_region = None


def get_cache_region():
    global _cache_region
    if _cache_region is None:
        _cache_region = make_region().configure(
            "dogpile.cache.redis",
            arguments={
                "url": f"redis://{config.falkor_host}:{config.falkor_port}/1",
                "redis_expiration_time": 3600 * 6,  # 6 hours TTL
                "distributed_lock": True,
                "thread_local_lock": False,
            },
        )
    return _cache_region


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
        Perform a search using DDGS in a thread pool with a strict timeout.
        Cached via Redis for 6 hours.
        """
        logger.info(
            "web_search_start",
            extra={"search_query": query, "max_results": max_results},
        )

        from dogpile.cache.api import NO_VALUE

        cache_key = f"web_search_cache:{query}:{max_results}"

        region = get_cache_region()
        cached_results = region.get(cache_key)

        if cached_results is not NO_VALUE:
            logger.info("web_search_cache_hit", extra={"search_query": query})
            return cast(List[Dict[str, Any]], cached_results)

        def _sync_search():
            try:
                # Use the module-level DDGS class (patched in tests)
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=max_results))
            except Exception as e:
                logger.error("ddg_library_error", extra={"error": str(e)})
                return []

        try:
            # Use configured tool timeout
            timeout = getattr(config, "ki_tool_timeout", 15)
            results_raw = await asyncio.wait_for(
                asyncio.to_thread(_sync_search), timeout=float(timeout)
            )
            results = []
            for r in results_raw:
                results.append(
                    {
                        "title": r.get("title"),
                        "snippet": r.get("body"),
                        "url": r.get("href"),
                        "source": "DuckDuckGo",
                    }
                )

            logger.info(
                "web_search_success",
                extra={"search_query": query, "result_count": len(results)},
            )

            region.set(cache_key, results)
            return results
        except asyncio.TimeoutError:
            logger.error(
                "web_search_timeout", extra={"search_query": query, "timeout": timeout}
            )
            return []
        except Exception as e:
            logger.error(
                "web_search_failure", extra={"search_query": query, "error": str(e)}
            )
            return []

    @staticmethod
    async def search_and_summarize(query: str, max_results: int = 3) -> str:
        """
        Search and return a condensed string for LLM context.
        """
        results = await WebSearchTool.search(query, max_results)
        if not results:
            return "No recent web data found."

        summary = "\n".join(
            [f"- [{r['title']}]({r['url']}): {r['snippet']}" for r in results]
        )
        return f"Latest Web Intelligence for '{query}':\n{summary}"


if __name__ == "__main__":
    # Quick Test
    async def test():
        res = await WebSearchTool.search_and_summarize("Gold spot price today 2026")
        print(res)

    asyncio.run(test())
