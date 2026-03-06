import asyncio
import os
import sys
import logging
from app.services.janitor_service import JanitorService
from app.core.scheduler import scheduler

# Add the project root to sys.path
sys.path.append(os.path.join(os.getcwd(), ".."))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("force-reconcile")

async def force_reconcile():
    """Manually triggers the Janitor reconciliation loop."""
    logger.info("🚀 Forcing Janitor reconciliation...")
    try:
        await JanitorService.reconcile_all_accounts()
        logger.info("✅ Forced reconciliation complete.")
    except Exception as e:
        logger.error(f"❌ Forced reconciliation failed: {e}")

if __name__ == "__main__":
    asyncio.run(force_reconcile())
