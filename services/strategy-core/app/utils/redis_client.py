import os
import redis.asyncio as aioredis
import logging

logger = logging.getLogger(__name__)

# Global singleton for Redis connection pool
_redis_client = None
_redis_pool = None

def get_redis_client():
    """
    Returns a globally shared, pooled Redis client.
    Thread-safe and efficient for HFT hot-paths.
    """
    global _redis_client, _redis_pool
    
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        logger.info(f"Initializing Global Redis Connection Pool: {redis_url}")
        
        _redis_pool = aioredis.ConnectionPool.from_url(
            redis_url,
            decode_responses=True,
            max_connections=20  # Tuning for strategy-core worker concurrency
        )
        _redis_client = aioredis.Redis(connection_pool=_redis_pool)
        
    return _redis_client

async def close_redis():
    """Cleanup pool on shutdown."""
    global _redis_client, _redis_pool
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_client = None
        _redis_pool = None
        logger.info("Global Redis Pool disconnected.")
