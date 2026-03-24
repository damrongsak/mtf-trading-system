import redis.asyncio as redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Global Redis Client and Pool for HFT caching
_redis_client = None
_redis_pool = None

def get_redis_client():
    """
    Returns a shared, pooled Redis client.
    Thread-safe and efficient for HFT hot paths.
    """
    global _redis_client, _redis_pool
    if _redis_client is None:
        if _redis_pool is None:
            _redis_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                max_connections=50  # Balanced for HFT scale
            )
        _redis_client = redis.Redis(connection_pool=_redis_pool)
        logger.info(f"🚀 Initialized pooled Global Redis client connected to {settings.REDIS_URL}")
    return _redis_client
