import asyncio
import logging
import os
import sys

# Ensure we can import app
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("stream_runner")

from app.streaming.manager import stream_manager
from app.services.calendar_service import calendar_service

async def run_calendar_scraper():
    """Runs calendar scraper every 4 hours"""
    while True:
        try:
            logger.info("Running scheduled Calendar Update...")
            await calendar_service.fetch_and_cache_events()
        except Exception as e:
            logger.error(f"Calendar scheduler failed: {e}")
        
        # Sleep for 4 hours
        await asyncio.sleep(4 * 3600)

async def main():
    logger.info("Initializing Stream Manager...")
    try:
        # Start Calendar Scraper in background
        asyncio.create_task(run_calendar_scraper())

        await stream_manager.start()
        
        # Keep process alive
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Stopping stream runner...")
        await stream_manager.stop()
    except Exception as e:
        logger.critical(f"Runner failed: {e}")
        await stream_manager.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
