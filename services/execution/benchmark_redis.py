
import asyncio
import time
import os
import redis.asyncio as aioredis
from app.utils.redis_client import get_redis_client

async def benchmark_old_way():
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    start = time.perf_counter()
    for _ in range(100):
        # The "old" way: create connection every time
        r = aioredis.from_url(redis_url, decode_responses=True)
        await r.ping()
        await r.aclose()
    end = time.perf_counter()
    return (end - start) / 100

async def benchmark_new_way():
    start = time.perf_counter()
    r = get_redis_client()
    for _ in range(100):
        # The "new" way: use pooled global client
        await r.ping()
    end = time.perf_counter()
    return (end - start) / 100

async def run():
    print("--- Redis Latency Benchmark (100 iterations) ---")
    old_avg = await benchmark_old_way()
    print(f"Old Way (New conn/close per op): {old_avg*1000:.4f} ms/op")
    
    new_avg = await benchmark_new_way()
    print(f"New Way (Pooled Global Client): {new_avg*1000:.4f} ms/op")
    
    improvement = ((old_avg - new_avg) / old_avg) * 100
    print(f"Improvement: {improvement:.2f}%")

if __name__ == "__main__":
    asyncio.run(run())
