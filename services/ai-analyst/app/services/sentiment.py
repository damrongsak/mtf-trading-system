import json
import redis.asyncio as redis
import logging
import hashlib
from app.core.config import settings
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

class SentimentService:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_FLASH_MODEL_ID,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1
        )
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.cache_ttl = 3600 # 1 hour

    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()

    async def get_sentiment(self, symbol: str = "XAUUSD") -> dict:
        if not settings.GOOGLE_API_KEY:
            return {"score": 0.0, "reason": "GOOGLE_API_KEY not configured."}

        # 1. Fetch News
        headlines = await self._fetch_news(symbol)
        if not headlines:
            return {"score": 0.0, "reason": "No recent news found."}

        # Calculate Headline Hash to avoid redundant analysis if news hasn't changed
        headlines_text = "".join(headlines)
        headlines_hash = hashlib.md5(headlines_text.encode()).hexdigest()
        
        # 2. Check Cache (with Hash)
        cache_key = f"sentiment:{symbol}"
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                cached_data = json.loads(cached)
                # If news hash matches, return cached result immediately
                if cached_data.get("headlines_hash") == headlines_hash:
                    logger.info(f"✨ Sentiment Cache HIT (Hash Match) for {symbol}. Skipping LLM.")
                    # Remove hash from response before returning to client
                    cached_data.pop("headlines_hash", None)
                    return cached_data
        except Exception as e:
            logger.error(f"Redis cache read failed: {e}")

        # 3. Analyze with Gemini (if cache miss or hash mismatch)
        result = await self._analyze_headlines(symbol, headlines)
        
        # Add hash to result for caching
        cached_result = {**result, "headlines_hash": headlines_hash}

        # 4. Persist to DB
        await self._save_sentiment_to_db(symbol, result)

        # 5. Save to Cache
        try:
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(cached_result))
            logger.info(f"💾 Cached new sentiment for {symbol} (Hash: {headlines_hash[:8]}...)")
        except Exception as e:
            logger.error(f"Redis cache write failed: {e}")
            
        return result

    async def _save_sentiment_to_db(self, symbol: str, result: dict):
        """Publish sentiment score to Redis Stream for persistence (Async RPC)."""
        payload = {
            "symbol": symbol,
            "score": str(result.get("score", 0.0)),
            "reason": result.get("reason", ""),
            "source_breakdown": json.dumps({}) # Placeholder
        }
        
        try:
            # Publish to stream - maxlen 1000 for history
            await self.redis.xadd("market.sentiment.stream", payload, maxlen=1000, approximate=True)
            logger.info(f"Published sentiment event for {symbol} to Redis Stream.")
        except Exception as e:
            logger.error(f"Error publishing sentiment to stream: {e}")

    async def _fetch_news(self, symbol: str) -> list[str]:
        """
        Fetches news headlines from Redis (ECST pattern).
        The data-pipeline service is responsible for populating this cache.
        """
        cache_key = f"news:headlines:{symbol}"
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                headlines = json.loads(cached)
                # Headlines are list of dicts: {title, source, url, publishedAt}
                return [f"- {h['title']} ({h['source']})" for h in headlines]
            
            logger.warning(f"No headlines found in Redis for {symbol}. Ensure news-sync is running.")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch news from Redis: {e}")
            return []

    async def _analyze_headlines(self, symbol: str, headlines: list[str]) -> dict:
        headlines_text = "\n".join(headlines)
        prompt = (
            f"Analyze the following news headlines for {symbol} sentiment.\n"
            f"Headlines:\n{headlines_text}\n\n"
            "Task:\n"
            "1. Determine the overall market sentiment for this asset.\n"
            "2. Assign a score from -1.0 (Very Bearish) to 1.0 (Very Bullish).\n"
            "3. Provide a concise 1-sentence reason.\n\n"
            "Output Format (JSON only):\n"
            '{"score": 0.0, "reason": "..."}'
        )
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content.strip()
            
            # Simple parsing (robustness improvement: use structured output or PydanticOutputParser later)
            import json
            # Handle potential markdown fence
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()
            
            data = json.loads(content)
            return {
                "score": float(data.get("score", 0.0)),
                "reason": data.get("reason", "Analysis failed")
            }
        except Exception as e:
            logger.error(f"LLM Analysis Error: {e}")
            return {"score": 0.0, "reason": "Error parsing sentiment analysis."}
