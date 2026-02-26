import json
import redis.asyncio as redis
import logging
import hashlib
from app.core.config import settings
from app.core.schemas import SentimentResult
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.core.globals import services

logger = logging.getLogger(__name__)

class SentimentService:
    def __init__(self):
        # We now use the global gemini client from services dict
        self.redis = redis.from_url(settings.redis.url, decode_responses=True)
        self.cache_ttl = 900 # 15 minutes (synced with scheduler frequency)

    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()

    async def get_sentiment(self, symbol: str = "XAUUSD") -> dict:
        if not settings.gemini.api_key:
            return {"score": 0.0, "reason": "Gemini API Key not configured."}

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

        # 3. Analyze with Gemini (using GeminiClient with Tier 1 fallback)
        result = await self._analyze_headlines_optimized(symbol, headlines)
        
        # Add hash to result for caching
        cached_result = {**result, "headlines_hash": headlines_hash}

        # 4. Save to Cache (before DB to ensure fast subsequent reads)
        try:
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(cached_result))
            logger.info(f"💾 Cached new sentiment for {symbol} (Hash: {headlines_hash[:8]}...)")
        except Exception as e:
            logger.error(f"Redis cache write failed: {e}")

        # 5. Persist to DB (using Redis Stream)
        await self._save_sentiment_to_db(symbol, result)
            
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
        Truncates to latest 20 headlines to save tokens.
        """
        cache_key = f"news:headlines:{symbol}"
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                headlines = json.loads(cached)
                # Truncate to save context window/tokens
                headlines = headlines[:20]
                return [f"- {h['title']} ({h['source']})" for h in headlines]
            
            logger.warning(f"No headlines found in Redis for {symbol}. Ensure news-sync is running.")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch news from Redis: {e}")
            return []

    async def _analyze_headlines_optimized(self, symbol: str, headlines: list[str]) -> dict:
        """Analyzes sentiment using the Tier 1 Gemini fallback chain."""
        headlines_text = "\n".join(headlines)
        prompt = (
            f"Analyze {symbol} sentiment from these news headlines. "
            "Return JSON only: {'score': float (-1.0 to 1.0), 'reason': '1-sentence string'}.\n"
            f"Headlines:\n{headlines_text}"
        )
        
        gemini = services.get("gemini")
        if not gemini:
            logger.error("GeminiClient not found in global services.")
            return {"score": 0.0, "reason": "AI Service Unavailable"}

        try:
            # Use Tier 1 models (Flash Lite) for background cost efficiency
            models = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash"]
            response = await gemini.generate_content(
                contents=[prompt],
                model=models,
                response_schema=SentimentResult
            )
            
            if not response or not response.get("text"):
                return {"score": 0.0, "reason": "Empty AI response"}

            # Robust JSON parsing using Pydantic
            data = SentimentResult.model_validate_json(response["text"])
            return {
                "score": data.score,
                "reason": data.reason
            }
        except Exception as e:
            logger.error(f"Sentiment LLM Analysis Error: {e}")
            return {"score": 0.0, "reason": "Error parsing sentiment result."}
