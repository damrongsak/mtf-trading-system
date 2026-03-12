from pydantic import BaseModel, Field
from typing import Any, Optional, Type
import aiohttp
import json
import logging
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class GoogleSearchInput(BaseModel):
    query: str = Field(..., description="The search query or keyword (e.g. 'XAUUSD news')")

class GoogleSearchTool(BaseTool):
    """
    Standardized tool for gathering market news and context.
    Provides news from internal data pipeline (scrapers/RSS) with semantic fallbacks.
    """
    name: str = "google_search"
    description: str = "Fetches real-time market news and institutional context. Use this to find sentiment and fundamental drivers."
    args_schema: Type[BaseModel] = GoogleSearchInput
    is_heavy: bool = True

    async def run_tool(self, input_data: Any, **kwargs) -> str:
        query = ""
        if hasattr(input_data, "dict"):
            input_data = input_data.dict()
            
        if isinstance(input_data, dict):
            query = input_data.get("query", "")
        elif isinstance(input_data, str):
            query = input_data

        # Extract auth_token from kwargs
        auth_token = kwargs.get("auth_token")
        
        if not query:
            return "No query provided for search."

        # 1. Attempt to fetch from StateCache (ECST - Zero I/O) first
        symbol_to_check = "XAUUSD" # Default
        upper_query = query.upper()
        if "GOLD" in upper_query or "XAU" in upper_query:
            symbol_to_check = "XAUUSD"
        elif "EUR" in upper_query:
            symbol_to_check = "EURUSD"
        elif "BITCOIN" in upper_query or "BTC" in upper_query:
            symbol_to_check = "BTCUSD"

        # Check local memory first
        from app.utils.state_cache import state_cache
        context_key = f"market_context:{symbol_to_check}"
        cached_context = state_cache.get(context_key)
        
        if cached_context:
            logger.info(f"SearchTool: ECST HIT for {context_key}")
            return cached_context.get("context", "No context found.")

        # 2. ECST MISS: Attempt to fetch from Redis L2 Cache
        try:
            redis = aioredis.from_url(settings.redis.url, decode_responses=True)
            cached_data = await redis.get(context_key)
            if cached_data:
                data = json.loads(cached_data)
                logger.info(f"SearchTool: Redis HIT for {symbol_to_check}")
                # Backfill StateCache for O(1) next time
                state_cache.set_local(context_key, data)
                await redis.aclose()
                return data.get("context", "No context found.")
            await redis.aclose()
        except Exception as e:
            logger.error(f"SearchTool Redis error: {e}")

        # 3. Cache MISS: Check ECST for News Headlines
        news_key = f"news:headlines:{symbol_to_check}"
        cached_news = state_cache.get(news_key)
        if cached_news and isinstance(cached_news, list):
            logger.info(f"SearchTool: ECST News HIT for {news_key}")
            results = [f"--- Internal News Feed (ECST) for {symbol_to_check} ---"]
            for item in cached_news[:5]:
                if isinstance(item, dict) and item.get("title"):
                    results.append(f"News: {item.get('title')}\nSource: {item.get('source', 'Unknown')} ({item.get('publishedAt', 'Recent')})\n")
            if len(results) > 1:
                return "\n".join(results)

        # 4. Final Attempt: Call Internal News API via Data Pipeline (Avoid Gateway for reentrancy)
        logger.info(f"SearchTool: Full MISS for {query}. Fetching from internal News API.")
        try:
            # Map query keywords to symbol for internal API
            api_url = f"{settings.DATA_PIPELINE_URL}/api/v1/news/headlines"
            params = {"symbol": symbol_to_check, "count": 10}
            headers = {"Authorization": auth_token if auth_token and auth_token.startswith("Bearer ") else f"Bearer {auth_token}"} if auth_token else {}
            
            timeout = aiohttp.ClientTimeout(total=5.0, connect=2.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(api_url, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        raw_data = await resp.json()
                        # Handle both {"data": [...]} and [...] formats
                        news_items = raw_data.get("data", []) if isinstance(raw_data, dict) else raw_data
                        
                        if news_items and isinstance(news_items, list):
                            # Populate StateCache for future O(1)
                            state_cache.set_local(news_key, news_items)
                            
                            results = [f"--- Internal News Feed for {symbol_to_check} ---"]
                            for item in news_items[:5]:
                                if isinstance(item, dict) and item.get("title"):
                                    title = item.get("title")
                                    source = item.get("source", "Unknown Source")
                                    date = item.get("published_at", item.get("publishedAt", "Unknown Date"))
                                    results.append(f"News: {title}\nSource: {source} ({date})\n")
                            
                            if len(results) > 1:
                                return "\n".join(results)
                            return f"No valid news articles found for '{symbol_to_check}'."
                    else:
                        logger.warning(f"Internal News API returned {resp.status}")
        except Exception as e:
            logger.error(f"Internal news fetch failed: {e}")

        # 3. Final Fallback: Semantic Narrative
        logger.warning(f"All news sources failed for {query}. Using semantic fallback.")
        return (
            f"[MARKET NARRATIVE for '{symbol_to_check}']\n"
            "Live news feeds are temporarily unavailable. Current institutional focus for XAUUSD:\n"
            "- Geopolitical risk premium remains elevated due to Middle East tensions.\n"
            "- Macro drivers: Pivot towards safe-haven assets amid US Dollar volatility.\n"
            "- Technical Bias: Strong structural support confirmed at recent order blocks.\n"
            "- Note: Please refer to 'smc_technical_analysis' and 'open_interest' tools for specific price levels."
        )
