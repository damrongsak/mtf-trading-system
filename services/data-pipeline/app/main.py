from fastapi import FastAPI
from app.routes import router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.scheduler.jobs import run_ingestion_job, run_calendar_sync_job, run_news_sync_job, run_trade_sync_job, run_cot_sync_job
from app.logging_config import setup_logging
import logging
import asyncio

# Configure logging
logger = setup_logging()

app = FastAPI(title="Data Pipeline Service")

app.include_router(router)

# Scheduler
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def start_scheduler():
    logger.info(f"Starting scheduler...")
    from app.database import engine
    logger.info(f"Database Pool Size: {engine.pool.size()}")
    # Schedule ingestion every 5 minutes (Optimized for RAM/CPU)
    scheduler.add_job(run_ingestion_job, 'interval', minutes=5, id='ingestion_job', misfire_grace_time=60)
    
    # Schedule Economic Calendar every 1 hour
    scheduler.add_job(run_calendar_sync_job, 'interval', hours=1, id='calendar_sync_job', misfire_grace_time=300)
    
    # Schedule News Sync every 1 hour
    scheduler.add_job(run_news_sync_job, 'interval', hours=1, id='news_sync_job', misfire_grace_time=300)

    # Schedule Trade Sync every 5 minutes (cTrader Rate Limit Friendly)
    scheduler.add_job(run_trade_sync_job, 'interval', minutes=5, id='trade_sync_job', misfire_grace_time=60)

    # Schedule COT Sync every 1 day
    scheduler.add_job(run_cot_sync_job, 'interval', days=1, id='cot_sync_job', misfire_grace_time=3600)
    
    scheduler.start()
    
    # Trigger COT once on startup to ensure data is current
    asyncio.create_task(run_cot_sync_job())
    
    # Start Stream Manager
    from app.streaming.manager import stream_manager
    await stream_manager.start()

    # Start Sentiment Worker (Decoupled Persistence)
    from app.workers.sentiment_worker import sentiment_worker
    await sentiment_worker.start()

    # Feature Worker (MOVED TO STRATEGY-CORE)
    # from app.workers.feature_worker import FeatureWorker
    # global feature_worker
    # feature_worker = FeatureWorker()
    # await feature_worker.start()

@app.on_event("shutdown")
async def shutdown_scheduler():
    scheduler.shutdown()
    from app.streaming.manager import stream_manager
    await stream_manager.stop()
    
    # if 'feature_worker' in globals():
    #     await feature_worker.stop()

@app.get("/health")
def health_check():
    return {
        "status": "ok", 
        "service": "data-pipeline",
        "scheduler": "running" if scheduler.running else "stopped"
    }
