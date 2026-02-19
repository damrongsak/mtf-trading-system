import asyncio
import time
import msgpack
import redis.asyncio as redis
from app.streaming.efp_engine import EFPEngine

async def benchmark_efp_engine():
    engine = EFPEngine()
    iterations = 10000
    
    print(f"Warming up EFPEngine...")
    for _ in range(100):
        engine.update(2700.50, 2700.55, 2715.20, 2715.25, time.time())
    
    print(f"Benchmarking EFPEngine over {iterations} iterations...")
    
    start_time = time.perf_counter()
    for i in range(iterations):
        engine.update(2700.50, 2700.55, 2715.20, 2715.25, time.time())
    end_time = time.perf_counter()
    
    avg_latency = (end_time - start_time) / iterations * 1e6 # in microseconds
    print(f"Average EFPEngine Latency: {avg_latency:.2f} μs")

async def benchmark_redis_binary_publish():
    r = redis.from_url("redis://redis:6379/0")
    iterations = 1000
    test_payload = {"s": 14.7, "t": time.time(), "b": 2700.5, "a": 2700.6, "fb": 2715.2, "fa": 2715.3}
    
    print(f"Benchmarking Redis Binary Publish over {iterations} iterations...")
    
    start_time = time.perf_counter()
    for i in range(iterations):
        payload = msgpack.packb(test_payload, use_bin_type=True)
        await r.publish("benchmark:efp", payload)
    end_time = time.perf_counter()
    
    avg_latency = (end_time - start_time) / iterations * 1e6
    print(f"Average Redis Publish Latency: {avg_latency:.2f} μs")
    await r.close()

if __name__ == "__main__":
    asyncio.run(benchmark_efp_engine())
    asyncio.run(benchmark_redis_binary_publish())
