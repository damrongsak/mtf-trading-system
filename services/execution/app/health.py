import logging
import os
import asyncio
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
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        # Use a short timeout for the check
        r = redis.from_url(redis_url, socket_connect_timeout=3, socket_timeout=3)
        await r.ping()
        await r.close()
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
