import redis.asyncio as redis
import json
import logging
import os

logger = logging.getLogger(__name__)

class RedisPublisher:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.redis = None

    async def connect(self):
        if not self.redis:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            logger.info(f"Connected to Redis at {self.redis_url}")

    async def publish(self, channel: str, message: dict):
        if not self.redis:
            await self.connect()
        try:
            # Ensure datetime objects are serialized to ISO format
            def json_serial(obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                return str(obj)

            await self.redis.publish(channel, json.dumps(message, default=json_serial))
        except Exception as e:
            logger.error(f"Failed to publish to {channel}: {e}")

    async def close(self):
        if self.redis:
            await self.redis.close()
            self.redis = None
