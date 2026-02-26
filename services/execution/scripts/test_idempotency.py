import asyncio
import json
import uuid
import redis.asyncio as redis
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IdempotencyTest")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
QUEUE_NAME = "queue:execution:commands"

async def test_idempotency():
    logger.info("--- Starting Async Idempotency (SETNX) Test ---")
    r = redis.from_url(REDIS_URL, decode_responses=True)
    
    # 1. Create a single unique fake order ID
    test_client_order_id = str(uuid.uuid4())
    logger.info(f"Generated test order UUID: {test_client_order_id}")
    
    payload = {
        "client_order_id": test_client_order_id,
        "symbol": "XAUUSD",
        "direction": "BULLISH",
        "lot_size": 0.5,
        "type": "order"
    }
    
    # 2. Fire 3 identical orders into the queue simultaneously
    logger.info("Pushing 3 identical messages into Execution Queue...")
    pipeline = r.pipeline()
    for _ in range(3):
        pipeline.lpush(QUEUE_NAME, json.dumps(payload))
    
    await pipeline.execute()
    
    logger.info("✅ All 3 messages injected successfully.")
    logger.info("Please check 'docker compose logs -f execution' to verify that ONLY ONE order is processed, and the other 2 trigger an 'Idempotency Reject' warning.")
    
    await r.aclose()

if __name__ == "__main__":
    asyncio.run(test_idempotency())
