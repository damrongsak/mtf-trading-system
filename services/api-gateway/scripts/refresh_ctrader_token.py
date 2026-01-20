
import asyncio
import logging
import sys
import os

# Add parent directory to path to import app
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models.broker_account import BrokerAccount
from app.services.auth_service import refresh_ctrader_token_internal

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TokenRefresh")

async def refresh_all():
    logger.info("Starting Manual Token Refresh...")
    db = SessionLocal()
    try:
        accounts = db.query(BrokerAccount).filter(
            BrokerAccount.broker_name == "CTRADER", 
            BrokerAccount.is_active == True
        ).all()
        
        if not accounts:
            logger.info("No active cTrader accounts found.")
            return

        for account in accounts:
            logger.info(f"Refreshing account {account.account_name} ({account.id})...")
            success = await refresh_ctrader_token_internal(account, db, force=True)
            if success:
                logger.info("SUCCESS")
            else:
                logger.error(f"FAILED to refresh account {account.account_name}")
                
    except Exception as e:
        logger.error(f"Script failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(refresh_all())
