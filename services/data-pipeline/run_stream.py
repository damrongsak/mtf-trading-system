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
async def main():
    logger.info("Initializing Stream Manager...")
    try:
        # Note: Calendar and News jobs are now handled by the main scheduler in app/main.py
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
