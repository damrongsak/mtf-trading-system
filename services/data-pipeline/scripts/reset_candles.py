
import asyncio
import logging
import argparse
from datetime import datetime, timedelta, timezone
from app.database import SessionLocal
from app.repositories.candle_repository import CandleRepository
from app.scheduler.jobs import run_ingestion_job

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("reset_candles")

async def reset_and_reload(days: int):
    """
    Truncate the candles table and trigger a fresh reload from cTrader.
    """
    db = SessionLocal()
    try:
        candle_repo = CandleRepository(db)
        
        # 1. Truncate Table
        logger.info("Cleaning candles table...")
        candle_repo.truncate_candles()
        logger.info("Candles table cleaned.")
        
        # 2. Define Backfill Range
        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(days=days)
        
        logger.info(f"Triggering fresh reload for the last {days} days ({from_date} to {to_date})...")
        
        # 3. Run Ingestion Job
        # This will iterate through active data sources (cTrader, OANDA) and backfill
        await run_ingestion_job(
            from_date=from_date,
            to_date=to_date
        )
        
        logger.info("Reload process initiated successfully.")
        
    except Exception as e:
        logger.error(f"Failed to reset and reload candles: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean candles table and reload data from brokers.")
    parser.add_argument("--days", type=int, default=30, help="Number of days to backfill (default: 30)")
    
    args = parser.parse_args()
    
    asyncio.run(reset_and_reload(args.days))
