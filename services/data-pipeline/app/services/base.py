import logging
import aiohttp
import json
from typing import Optional, Any
from redis import asyncio as aioredis  # type: ignore
from app.core.config import settings

logger = logging.getLogger(__name__)

class BaseService:
    """
    Base class for services requiring Redis or HTTP capabilities.
    """
    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_redis(self) -> aioredis.Redis:
        """Lazy initialization of Redis connection."""
        if not self._redis:
            self._redis = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    async def get_session(self) -> aiohttp.ClientSession:
        """Lazy initialization of ClientSession."""
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Cleanup resources."""
        if self._redis:
            await self._redis.close()
            self._redis = None
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _cache_get(self, key: str) -> Optional[Any]:
        """Helper to get parsed JSON from cache."""
        redis = await self.get_redis()
        data = await redis.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                logger.warning(f"Failed to decode cache key: {key}")
                return None
        return None

    async def _cache_set(self, key: str, value: Any, ttl: int = 3600):
        """Helper to set JSON data to cache."""
        redis = await self.get_redis()
        try:
            dumped = json.dumps(value)
            await redis.set(key, dumped, ex=ttl)
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
