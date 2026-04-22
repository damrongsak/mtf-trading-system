import redis.asyncio as redis
import json
import logging
import os
import msgpack

logger = logging.getLogger(__name__)

class RedisPublisher:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.redis = None

    async def connect(self):
        if not self.redis:
            self.redis = redis.from_url(self.redis_url, decode_responses=False) # Use binary responses
            logger.info(f"Connected to Redis at {self.redis_url}")

    async def publish_binary(self, channel: str, message: dict):
        """Publish a message as binary using msgpack."""
        if not self.redis:
            await self.connect()
        try:
            payload = msgpack.packb(message, use_bin_type=True)
            await self.redis.publish(channel, payload)
        except Exception as e:
            logger.error(f"Failed to publish binary to {channel}: {e}")

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

    async def publish_with_cache(self, channel: str, cache_key: str, message: dict, cache_mapping: dict):
        """Publish a message and update a hash cache atomically using a pipeline."""
        if not self.redis:
            await self.connect()
        try:
            def json_serial(obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                return str(obj)

            msg_str = json.dumps(message, default=json_serial)
            pipe = self.redis.pipeline()
            pipe.publish(channel, msg_str)
            pipe.hset(cache_key, mapping=cache_mapping)
            await pipe.execute()
        except Exception as e:
            logger.error(f"Failed to publish and cache to {channel}/{cache_key}: {e}")

    async def xadd(self, stream_key: str, fields: dict, id="*", maxlen: int = 10000):
        """Append a message to a stream."""
        if not self.redis:
            await self.connect()
        try:
             # Redis streams require dict values to be strings (usually) or bytes.
             # We should ensure fields are serialized if they aren't simple strings/flat.
             # But standard xadd takes a dict. We'll rely on redis-py to handle basic types,
             # or convert non-primitives to JSON strings.
             safe_fields = {}
             for k, v in fields.items():
                 if isinstance(v, (dict, list)):
                     safe_fields[k] = json.dumps(v, default=str)
                 else:
                     safe_fields[k] = str(v)
            
             return await self.redis.xadd(stream_key, safe_fields, id=id, maxlen=maxlen, approximate=True)
        except Exception as e:
            logger.error(f"Failed to xadd to {stream_key}: {e}")
            return None

    async def close(self):
        if self.redis:
            await self.redis.aclose()
            self.redis = None
