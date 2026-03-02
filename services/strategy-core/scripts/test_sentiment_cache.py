import asyncio
import time
import redis.asyncio as redis
import os
import logging
from app.adapters.ai_analyst import get_market_sentiment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SentimentTest")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

async def test_sentiment():
    logger.info("--- 1. Injecting Mock Sentiment into Redis ---")
    r = redis.from_url(REDIS_URL, decode_responses=True)
    
    # Mock data identical to AI Analyst output
    mock_payload = '{"score": 0.85, "reason": "Strong Bullish News on Gold"}'
    await r.set("sentiment:XAUUSD", mock_payload, ex=900)
    logger.info(f"Injected: {mock_payload}")
    await r.aclose()
    
    logger.info("--- 2. Strategy Core Fetching Sentiment ---")
    start_time = time.perf_counter()
    
    # The adapter should now read from Redis < 1ms instead of blocking HTTP
    result = await get_market_sentiment("XAUUSD")
    
    end_time = time.perf_counter()
    elapsed_ms = (end_time - start_time) * 1000
    
    logger.info(f"Result: {result}")
    logger.info(f"Fetch Time: {elapsed_ms:.2f} ms")
    
    if elapsed_ms < 10.0:
        logger.info("✅ SUCCESS: Sentiment fetch is non-blocking and Ultra-Fast (< 10ms)")
    else:
        logger.warning(f"⚠️ Warning: Fetch took longer than expected: {elapsed_ms:.2f} ms")

if __name__ == "__main__":
    asyncio.run(test_sentiment())
