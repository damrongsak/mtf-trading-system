import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

import logging
import asyncio
from sqlalchemy import text
from app.database import SessionLocal
from app.core.config import settings
from app.streaming.publisher import RedisPublisher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("startup-check")

async def check_database():
    """Verify Database connectivity and core tables."""
    logger.info("Checking Database connectivity...")
    db = SessionLocal()
    try:
        # 1. Connection check
        db.execute(text("SELECT 1"))
        logger.info("  - Database connection: OK")

        # 2. Core tables check
        required_tables = [
            "market_symbols",
            "candles",
            "data_sources",
            "economic_events",
            "cot_records",
            "sentiment_scores",
            "news_articles"
        ]
        
        for table in required_tables:
            query = text(f"SELECT 1 FROM {table} LIMIT 1")
            db.execute(query)
            logger.info(f"  - Table {table}: OK")

        # 3. Active data source check
        query = text("SELECT count(*) FROM data_sources WHERE is_active = true")
        active_count = db.execute(query).scalar()
        if active_count == 0:
            logger.warning("  - Active Data Sources: None found! (Service might start but won't ingest data)")
        else:
            logger.info(f"  - Active Data Sources: {active_count} found")

        return True
    except Exception as e:
        logger.error(f"  - Database check FAILED: {e}")
        return False
    finally:
        db.close()

async def check_redis():
    """Verify Redis connectivity."""
    logger.info("Checking Redis connectivity...")
    publisher = RedisPublisher()
    try:
        await publisher.connect()
        # Ping check
        if await publisher.redis.ping():
            logger.info("  - Redis connection: OK")
            return True
        else:
            logger.error("  - Redis ping: FAILED")
            return False
    except Exception as e:
        logger.error(f"  - Redis check FAILED: {e}")
        return False
    finally:
        await publisher.close()

async def main():
    logger.info("=== Starting Data-Pipeline Dry Run Check ===")
    
    db_ok = await check_database()
    redis_ok = await check_redis()
    
    if db_ok and redis_ok:
        logger.info("=== [PASS] All systems ready for startup ===")
        sys.exit(0)
    else:
        logger.error("=== [FAIL] Startup check failed! Service will not start. ===")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
