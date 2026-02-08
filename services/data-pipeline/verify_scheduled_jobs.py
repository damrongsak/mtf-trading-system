import asyncio
import logging
from app.database import SessionLocal
from app.scheduler.jobs import run_calendar_sync_job, run_news_sync_job, run_ingestion_job
from app.models.economic_event import EconomicEvent
from app.models.news import NewsArticle
from sqlalchemy import func

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verification")

async def verify():
    db = SessionLocal()
    try:
        logger.info("Starting verification of scheduled jobs...")
        
        # 1. Test Calendar Sync
        logger.info("Triggering Calendar Sync Job...")
        await run_calendar_sync_job()
        
        event_count = db.query(func.count(EconomicEvent.id)).scalar()
        logger.info(f"Total Economic Events in DB: {event_count}")
        
        # 2. Test News Sync
        logger.info("Triggering News Sync Job...")
        await run_news_sync_job()
        
        news_count = db.query(func.count(NewsArticle.id)).scalar()
        logger.info(f"Total News Articles in DB: {news_count}")
        
        # 3. Test Ingestion Job
        logger.info("Triggering Ingestion Job...")
        await run_ingestion_job()
        
        from app.models.candle import Candle
        candle_count = db.query(func.count(Candle.id)).scalar()
        logger.info(f"Total Candles in DB: {candle_count}")
        
        # 4. Test Deduplication (Run again)
        logger.info("Running sync jobs again to verify deduplication...")
        await run_calendar_sync_job()
        await run_news_sync_job()
        
        new_event_count = db.query(func.count(EconomicEvent.id)).scalar()
        new_news_count = db.query(func.count(NewsArticle.id)).scalar()
        
        logger.info(f"Economic Events after second run: {new_event_count} (Expected: {event_count})")
        logger.info(f"News Articles after second run: {new_news_count} (Expected: {news_count})")
        
        if new_event_count == event_count and new_news_count == news_count:
            logger.info("SUCCESS: Deduplication is working correctly.")
        else:
            logger.error("FAILURE: Deduplication failed. Duplicates detected.")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(verify())
