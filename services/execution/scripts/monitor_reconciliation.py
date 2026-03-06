import asyncio
import os
import sys
import logging
from sqlalchemy import text
from app.database import AsyncSessionLocal

# Add the project root to sys.path
sys.path.append(os.path.join(os.getcwd(), ".."))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("reconcile-monitor")

async def monitor_trade_reconciliation(broker_trade_id: str):
    """Monitors a specific trade for state reconciliation using broker_trade_id."""
    logger.info(f"Starting monitor for Broker Trade ID: {broker_trade_id}")
    
    while True:
        async with AsyncSessionLocal() as db:
            try:
                # Fetch trade status by broker_trade_id
                query = text("SELECT trade_id, status, updated_at FROM trades WHERE broker_trade_id = :bid")
                result = await db.execute(query, {"bid": broker_trade_id})
                row = result.fetchone()
                
                if not row:
                    logger.warning(f"Trade with Broker ID {broker_trade_id} not found in database yet...")
                else:
                    trade_id, status, updated_at = row
                    logger.info(f"Olympus ID: {trade_id} | Status: {status} | Last Update: {updated_at}")
                    
                    if status in ["CLOSED", "CLOSED_EXTERNALLY"]:
                        logger.info(f"✅ Trade {broker_trade_id} successfully reconciled to status: {status}")
                        break
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error during monitoring: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python monitor_reconciliation.py <broker_trade_id>")
        sys.exit(1)
    
    bid = sys.argv[1]
    asyncio.run(monitor_trade_reconciliation(bid))
