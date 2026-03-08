
import asyncio
import logging
import sys
import os
from datetime import datetime

# Ensure app is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.services.open_interest_service import OpenInterestService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ImportOI")

async def import_oi(file_path: str):
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return

    db = SessionLocal()
    try:
        logger.info(f"Reading OI file: {file_path}")
        with open(file_path, "rb") as f:
            content = f.read()

        logger.info("Parsing and storing OI data...")
        # OpenInterestService.parse_and_store is sync, but handles its own threading/db
        # Actually it uses db.execute which is sync, and it's called with loop.run_in_executor in routes?
        # Let's check the service again. It takes a Session.
        
        result = OpenInterestService.parse_and_store(content, db)
        
        if result.get("status") == "success":
            logger.info(f"Import successful: {result.get('records_processed')} records processed for {result.get('snapshot_at')}")
        else:
            logger.warning(f"Import finished with status: {result.get('status')}")

    except Exception as e:
        logger.error(f"Failed to import OI data: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        db.close()

if __name__ == "__main__":
    # Path relative to the script or absolute in container
    # Since it's run via docker compose exec as: python scripts/import_oi_data.py
    # and /app is services/data-pipeline
    target_file = "/app/data/gold_oi_matrix.xlsx"
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    
    asyncio.run(import_oi(target_file))
