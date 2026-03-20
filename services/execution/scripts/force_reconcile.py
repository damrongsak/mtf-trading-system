import asyncio
import os
import sys
import logging
from app.services.sync_service import SyncService

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("force-reconcile")

async def force_reconcile():
    """Manually triggers the SyncService reconciliation loop."""
    logger.info("🚀 Forcing SyncService reconciliation...")
    try:
        await SyncService.reconcile_all_funds()
        logger.info("✅ Forced reconciliation complete.")
    except Exception as e:
        logger.error(f"❌ Forced reconciliation failed: {e}")

if __name__ == "__main__":
    asyncio.run(force_reconcile())
