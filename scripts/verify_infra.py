import os
import sys
import asyncio
import logging
from redis.asyncio import Redis
import sqlalchemy
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("infra-validator")

async def verify_redis():
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    logger.info(f"🔍 Checking Redis at {redis_url}...")
    try:
        redis = Redis.from_url(redis_url)
        modules = await redis.execute_command("MODULE LIST")
        module_names = [m[1].decode('utf-8') if isinstance(m[1], bytes) else m[1] for m in modules]
        
        required = ["search", "ReJSON"]
        missing = [m for m in required if m not in module_names]
        
        if missing:
            logger.error(f"❌ Missing Redis Modules: {missing}")
            logger.error("👉 Root Cause: Redis 'command' override in docker-compose.yml might be blocking module loading.")
            return False
        
        logger.info(f"✅ Redis Modules Verified: {module_names}")
        return True
    except Exception as e:
        logger.error(f"❌ Redis Connection Failed: {e}")
        return False

async def verify_postgres():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.warning("⚠️ DATABASE_URL not set, skipping Postgres check.")
        return True
    
    # Convert sync driver to async if needed
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    logger.info("🔍 Checking PostgreSQL Connection...")
    try:
        engine = create_async_engine(db_url)
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT version();"))
            version = res.scalar()
            logger.info(f"✅ PostgreSQL Version: {version}")
        await engine.dispose()
        return True
    except Exception as e:
        logger.error(f"❌ PostgreSQL Connection Failed: {e}")
        return False

async def main():
    logger.info("🚀 Starting Infrastructure Validation...")
    results = await asyncio.gather(verify_redis(), verify_postgres())
    
    if all(results):
        logger.info("✨ Infrastructure Validation PASSED")
        sys.exit(0)
    else:
        logger.error("💥 Infrastructure Validation FAILED")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
