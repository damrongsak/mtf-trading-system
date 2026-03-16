import pytest
import time
import asyncio
from app.streaming.publisher import RedisPublisher

@pytest.mark.asyncio
async def test_redis_publisher_throughput():
    """
    Benchmark how many messages per second we can publish to Redis.
    Requires a running Redis instance (available in Docker/CI).
    """
    publisher = RedisPublisher()
    try:
        await publisher.connect()
        
        start_time = time.time()
        msg_count = 1000
        
        for i in range(msg_count):
            await publisher.publish("benchmark:test", {"seq": i, "ts": time.time()})
            
        duration = time.time() - start_time
        throughput = msg_count / duration
        
        print(f"\nRedis Publish Throughput: {throughput:.2f} msgs/sec")
        
        # Expectation: > 50 msgs/sec for local redis
        assert throughput > 50, "Throughput is surprisingly low (<50/s)"
        
    except ConnectionError:
        pytest.skip("Redis not available for performance test")
    finally:
        await publisher.close()
