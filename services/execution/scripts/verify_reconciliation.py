import asyncio
import logging
from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models import BrokerAccount, Fund, User, UserPreferences, UserFund
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_models():
    logger.info("Verifying database models and multi-tenant links...")
    async with AsyncSessionLocal() as db:
        # 1. Check if the new columns exist
        try:
            # Check UserPreferences.oanda_janitor_enabled
            await db.execute(text("SELECT oanda_janitor_enabled FROM user_preferences LIMIT 1"))
            logger.info("✅ Column 'user_preferences.oanda_janitor_enabled' exists.")
            
            # Check Trade.broker_trade_id
            await db.execute(text("SELECT broker_trade_id FROM trades LIMIT 1"))
            logger.info("✅ Column 'trades.broker_trade_id' exists.")
        except Exception as e:
            logger.error(f"❌ Missing columns: {e}")
            return False

        # 2. Verify Multi-Tenant Join Logic
        # We'll try to find any active OANDA accounts
        stmt = (
            select(BrokerAccount)
            .join(Fund, BrokerAccount.fund_id == Fund.id)
            .join(UserFund, Fund.id == UserFund.fund_id)
            .join(User, UserFund.user_id == User.id)
            .join(UserPreferences, User.id == UserPreferences.user_id)
            .where(
                BrokerAccount.broker_name == "OANDA",
                BrokerAccount.is_active == True
            )
        )
        
        result = await db.execute(stmt)
        accounts = result.scalars().all()
        logger.info(f"Found {len(accounts)} active OANDA accounts via link chain.")
        
        for acc in accounts:
            logger.info(f"Account: {acc.account_name}, Number: {acc.account_number}")
            
    return True

if __name__ == "__main__":
    asyncio.run(verify_models())
