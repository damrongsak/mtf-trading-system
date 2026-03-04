import os
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
            cls._instance.client = None
            cls._instance.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        return cls._instance

    async def get_client(self):
        if self.client is None:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            logger.info(f"Connected to Redis at {self.redis_url}")
        return self.client

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None

redis_client = RedisClient()

async def get_redis_client():
    """Backward compatibility helper."""
    return await redis_client.get_client()
