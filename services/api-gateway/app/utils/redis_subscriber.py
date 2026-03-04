import redis.asyncio as redis
import json
import logging
import os
import asyncio

logger = logging.getLogger(__name__)

class RedisSubscriber:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.redis = None
        self.pubsub = None

    async def connect(self):
        if not self.redis:
            # We set decode_responses=False to handle binary data safely without UnicodeDecodeError
            self.redis = redis.from_url(self.redis_url, decode_responses=False)
            self.pubsub = self.redis.pubsub()
            logger.info(f"Connected to Redis at {self.redis_url} (Binary mode)")

    async def subscribe(self, channels: list):
        if not self.pubsub:
            await self.connect()
        await self.pubsub.subscribe(*channels)
        logger.info(f"Subscribed to {channels}")

    async def psubscribe(self, pattern: str):
        if not self.pubsub:
            await self.connect()
        await self.pubsub.psubscribe(pattern)
        logger.info(f"PSubscribed to pattern: {pattern}")

    async def unsubscribe(self):
        if self.pubsub:
            await self.pubsub.unsubscribe()

    async def get_message(self):
        if not self.pubsub:
            return None
        return await self.pubsub.get_message(ignore_subscribe_messages=True)

    async def listen(self):
        if not self.pubsub:
            await self.connect()
        
        async for message in self.pubsub.listen():
            yield message

    async def close(self):
        if self.pubsub:
             await self.pubsub.aclose()
        if self.redis:
            await self.redis.aclose()
            self.redis = None
