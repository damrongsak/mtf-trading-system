import os
import json
import logging
import httpx
from app.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
AI_ANALYST_URL = os.getenv("AI_ANALYST_URL", "http://ai-analyst:8000")

async def get_market_sentiment(symbol: str) -> dict:
    """
    Read AI Analyst sentiment score from Redis (Async/Fast).
    Returns: {"score": float, "reason": str} or None on failure.
    """
    try:
        r = get_redis_client()
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

async def get_knowledge_context(symbol: str) -> dict:
    """
    Fetch Knowledge Graph context from AI Analyst service (Direct call).
    Returns: {"symbol": str, "entities": list, "summary": str, "knowledge_score": float}
    """
    url = f"{AI_ANALYST_URL}/api/v1/ai/knowledge/context"
    params = {"symbol": symbol}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get("data", {})
            else:
                logger.warning(f"Knowledge Bridge returned HTTP {response.status_code} for {symbol}")
                return {"knowledge_score": 1.0, "summary": "Knowledge Bridge error (fallback to neutral)"}
    except Exception as e:
        logger.error(f"Failed to fetch knowledge context for {symbol}: {e}")
        return {"knowledge_score": 1.0, "summary": f"Connection error: {e}"}
