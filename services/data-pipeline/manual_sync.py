
import asyncio
import logging
from app.scheduler.jobs import run_trade_sync_job
from app.database import SessionLocal

# Setup basic logging
logging.basicConfig(level=logging.INFO)

async def main():
    print("Triggering Manual Trade Sync...")
    await run_trade_sync_job()
    print("Manual Trade Sync Complete.")

if __name__ == "__main__":
    asyncio.run(main())
