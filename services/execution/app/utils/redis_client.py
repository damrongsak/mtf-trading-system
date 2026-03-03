import redis.asyncio as redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Global Redis Client for HFT caching
redis_client = None

def get_redis_client():
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        logger.info(f"Initialized global Redis client connected to {settings.REDIS_URL}")
    return redis_client
