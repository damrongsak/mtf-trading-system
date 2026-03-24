import logging
import os
import redis.asyncio as redis
from sqlalchemy import text
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

async def verify_dependencies():
    """
    Checks connection to critical dependencies (Redis, Database).
    Raises an exception if any dependency is unreachable.
    """
    logger.info("Verifying system dependencies...")
    
    # 1. Check Redis
    from app.utils.redis_client import get_redis_client
    try:
        # Use the global pooled client for health check
        r = get_redis_client()
        await r.ping()
        logger.info("✅ Redis connection verified.")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        raise ConnectionError(f"Redis unavailable: {e}")

    # 2. Check Database
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        logger.info("✅ Database connection verified.")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise ConnectionError(f"Database unavailable: {e}")

    logger.info("All dependencies are healthy.")
