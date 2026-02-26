import asyncio
import redis.asyncio as redis
import uuid
import json

async def main():
    r = redis.from_url("redis://localhost:6379/0", decode_responses=True)
    
    # Push 5 VIP orders
    for i in range(5):
        order = {"id": str(uuid.uuid4()), "symbol": "XAUUSD", "type": "BUY", "priority": "VIP"}
        await r.lpush("queue:exec:vip", json.dumps(order))
        
    # Push 10 Retail orders
    for i in range(10):
        order = {"id": str(uuid.uuid4()), "symbol": "XAUUSD", "type": "BUY", "priority": "RETAIL"}
        await r.lpush("queue:exec:retail", json.dumps(order))

    # Push 2 Dead Letter
    for i in range(2):
        order = {"id": str(uuid.uuid4()), "symbol": "EURUSD", "error": "Max retries exceeded"}
        await r.lpush("queue:exec:dead", json.dumps(order))
        
    print("Spiked queues with test data!")
    await r.aclose()

if __name__ == "__main__":
    asyncio.run(main())
