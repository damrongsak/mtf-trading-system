import os
import json
import logging
import redis.asyncio as redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

async def get_market_sentiment(symbol: str) -> dict:
    """
    Read AI Analyst sentiment score from Redis (Async/Fast).
    Returns: {"score": float, "reason": str} or None on failure.
    """
    r = None
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        # Using a standard cache key for sentiment
        cache_key = f"sentiment:{symbol}"
        data_str = await r.get(cache_key)
        
        if data_str:
            data = json.loads(data_str)
            return data
        else:
            logger.debug(f"Sentiment cache miss for {symbol}. Returning neutral fallback.")
            return {"score": 0.0, "reason": "Sentiment cache miss (fallback to neutral)"}
    except Exception as e:
        logger.error(f"Failed to read sentiment from Redis for {symbol}: {e}")
        return {"score": 0.0, "reason": f"Redis read error: {e}"}
    finally:
        if r:
            await r.aclose()
