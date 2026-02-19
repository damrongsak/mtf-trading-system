import redis.asyncio as redis
import json
import logging
import os
import asyncio
import msgpack

logger = logging.getLogger(__name__)

class RedisSubscriber:
    def __init__(self, callback):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.redis = None
        self.pubsub = None
        self.callback = callback # params: channel, data
        self.is_running = False

    async def connect(self):
        if not self.redis:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            self.pubsub = self.redis.pubsub()
            self.is_running = True
            logger.info(f"Subscriber connected to Redis at {self.redis_url}")
            asyncio.create_task(self._listen())

    async def subscribe(self, channels: list[str]):
        if not self.pubsub:
            await self.connect()
        await self.pubsub.subscribe(*channels)
        logger.info(f"Subscribed to {channels}")

    async def psubscribe(self, patterns: list[str]):
        if not self.pubsub:
            await self.connect()
        await self.pubsub.psubscribe(*patterns)
        logger.info(f"Subscribed to patterns {patterns}")

    async def unsubscribe(self, channels: list[str]):
        if self.pubsub:
            await self.pubsub.unsubscribe(*channels)

    async def punsubscribe(self, patterns: list[str]):
        if self.pubsub:
            await self.pubsub.punsubscribe(*patterns)

    async def _listen(self):
        try:
            async for message in self.pubsub.listen():
                if message['type'] in ('message', 'pmessage'):
                    channel = message['channel']
                    raw_data = message['data']
                    data = None
                    
                    # Try msgpack first (Binary Path)
                    try:
                        data = msgpack.unpackb(raw_data, raw=False)
                    except Exception:
                        # Fallback to JSON
                        if isinstance(raw_data, bytes):
                            try:
                                data = json.loads(raw_data.decode('utf-8'))
                            except Exception:
                                pass
                        elif isinstance(raw_data, str):
                            try:
                                data = json.loads(raw_data)
                            except Exception:
                                pass
                    
                    if data is not None:
                        try:
                            await self.callback(channel, data)
                        except Exception as e:
                            logger.error(f"Error in subscriber callback for {channel}: {e}")
                    else:
                        logger.error(f"Failed to decode message from {channel}")
        except Exception as e:
            if self.is_running:
                logger.error(f"Redis listener loop error: {e}")
                # Reconnect logic could go here

    async def stop(self):
        self.is_running = False
        if self.pubsub:
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()
