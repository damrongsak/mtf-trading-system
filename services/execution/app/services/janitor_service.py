import logging
import asyncio
from typing import List, Dict, Any
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import BrokerAccount, User, UserPreferences, DataSource, Trade, TradeStatus
from app.adapters.factory import BrokerFactory
from app.utils.crypto import decrypt_data
from app.database import AsyncSessionLocal
from datetime import datetime

logger = logging.getLogger(__name__)

class JanitorService:
    @classmethod
    async def reconcile_all_accounts(cls):
        """
        [THE JANITOR] Periodic reconciliation loop for all OANDA accounts.
        """
        logger.info("🧹 [Janitor] Starting multi-account reconciliation...")
        
        async with AsyncSessionLocal() as db:
            # 1. Check System Level Data Source
            ds_stmt = select(DataSource).where(DataSource.provider == "OANDA", DataSource.is_active == True)
            ds_result = await db.execute(ds_stmt)
            oanda_ds = ds_result.scalar_one_or_none()
            
            if not oanda_ds:
                logger.warning("🧹 [Janitor] OANDA Data Source is inactive. Skipping reconciliation.")
                return

            # 2. Fetch all OANDA accounts with Active User and Janitor Enabled
            # Relationship: BrokerAccount -> Fund -> UserFund -> User -> UserPreferences
            from app.models import Fund, UserFund
            
            stmt = (
                select(BrokerAccount)
                .join(Fund, BrokerAccount.fund_id == Fund.id)
                .join(UserFund, Fund.id == UserFund.fund_id)
                .join(User, UserFund.user_id == User.id)
                .join(UserPreferences, User.id == UserPreferences.user_id)
                .where(
                    BrokerAccount.broker_name == "OANDA",
                    BrokerAccount.is_active == True,
                    User.is_active == True,
                    UserPreferences.oanda_janitor_enabled == True
                )
            )
            
            result = await db.execute(stmt)
            accounts = result.scalars().all()
            
            logger.info(f"🧹 [Janitor] Found {len(accounts)} active OANDA accounts. Verifying user consent...")
            
            for account in accounts:
                try:
                    # [PRO] Permission Check: Verify user still exists and has janitor enabled
                    # We need to find the user via Fund -> UserFund -> User
                    # But if we don't have those models, we should at least check UserPreferences if we can link it.
                    # As a shortcut for this environment, let's assume if BrokerAccount is active, we proceed, 
                    # but the SPEC requires User level check. 
                    # Let's perform a raw SQL check or add the necessary models if missing.
                    
                    await cls.reconcile_single_account(account, db)
                except Exception as e:
                    logger.error(f"🧹 [Janitor] Failed to reconcile account {account.id}: {e}")

        logger.info("🧹 [Janitor] Reconciliation cycle complete.")

    @classmethod
    async def reconcile_single_account(cls, account: BrokerAccount, db: AsyncSession):
        """
        Sync a single OANDA account with local DB.
        """
        logger.info(f"🧹 [Janitor] Reconciling account {account.account_name} ({account.account_number})")
        
        # 1. Fetch live trades from OANDA
        credentials = decrypt_data(account.credentials_encrypted)
        adapter = BrokerFactory.get_adapter("OANDA", credentials)
        
        broker_trades = await adapter.get_open_trades()
        broker_trade_ids = {str(t.get('id')) for t in broker_trades}
        
        # 2. Fetch open trades in Olympus DB for this account
        db_stmt = select(Trade).where(
            Trade.broker_account_id == account.id,
            Trade.status == TradeStatus.OPEN
        )
        db_result = await db.execute(db_stmt)
        olympus_trades = db_result.scalars().all()
        
        # 3. Detect Desynchronization
        for o_trade in olympus_trades:
            btid = o_trade.broker_trade_id
            
            if btid and str(btid) not in broker_trade_ids:
                logger.warning(f"⚠️ [Janitor] Desync Detected! Trade {o_trade.trade_id} (Broker: {btid}) is missing in OANDA. Closing in Olympus.")
                
                # Mark as CLOSED_EXTERNALLY in DB
                o_trade.status = TradeStatus.CLOSED
                o_trade.exit_timestamp = datetime.utcnow()
                if not o_trade.metadata_json:
                    o_trade.metadata_json = {}
                o_trade.metadata_json['janitor_close'] = True
                o_trade.metadata_json['close_reason'] = "CLOSED_EXTERNALLY_DETECTED_BY_JANITOR"
                
                # Commit will be handled by the session or caller
                
            else:
                # Trade is synchronized
                pass

        await db.commit()
        logger.info(f"🧹 [Janitor] Account {account.account_name} is now in sync.")
