from fastapi import FastAPI
from app.routes import router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.scheduler.jobs import run_ingestion_job
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Pipeline Service")

app.include_router(router)

# Scheduler
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def start_scheduler():
    logger.info("Starting scheduler...")
    # Schedule ingestion every 5 minutes (Optimized for RAM/CPU)
    scheduler.add_job(run_ingestion_job, 'interval', minutes=5, id='ingestion_job')
    scheduler.start()
    
    # Start Stream Manager
    from app.streaming.manager import stream_manager
    await stream_manager.start()

@app.on_event("shutdown")
async def shutdown_scheduler():
    scheduler.shutdown()
    from app.streaming.manager import stream_manager
    await stream_manager.stop()

@app.get("/health")
def health_check():
    return {
        "status": "ok", 
        "service": "data-pipeline",
        "scheduler": "running" if scheduler.running else "stopped"
    }
