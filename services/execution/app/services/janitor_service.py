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
        [THE JANITOR] Periodic reconciliation loop for all enabled brokers and users.
        """
        logger.info("🧹 [Janitor] Starting multi-account reconciliation...")
        
        async with AsyncSessionLocal() as db:
            # 1. Fetch active data sources to identify enabled providers
            ds_stmt = select(DataSource).where(DataSource.is_active == True)
            ds_result = await db.execute(ds_stmt)
            active_providers = {ds.provider for ds in ds_result.scalars().all()}
            
            # 2. Fetch all active users with their preferences
            from app.models import Fund, UserFund
            user_stmt = select(User, UserPreferences).join(UserPreferences, User.id == UserPreferences.user_id).where(User.is_active == True)
            user_result = await db.execute(user_stmt)
            users_with_prefs = user_result.all()
            
            total_synced = 0
            
            for user, prefs in users_with_prefs:
                # Determine which brokers are enabled for this specific user
                enabled_brokers = []
                if prefs.oanda_janitor_enabled and "OANDA" in active_providers:
                    enabled_brokers.append("OANDA")
                if hasattr(prefs, "ctrader_janitor_enabled") and prefs.ctrader_janitor_enabled and "CTRADER" in active_providers:
                    enabled_brokers.append("CTRADER")
                
                if not enabled_brokers:
                    continue
                
                # 3. Fetch all active broker accounts for this user that belong to enabled brokers
                acc_stmt = (
                    select(BrokerAccount)
                    .join(Fund, BrokerAccount.fund_id == Fund.id)
                    .join(UserFund, Fund.id == UserFund.fund_id)
                    .where(
                        UserFund.user_id == user.id,
                        BrokerAccount.is_active == True,
                        BrokerAccount.broker_name.in_(enabled_brokers)
                    )
                )
                acc_result = await db.execute(acc_stmt)
                accounts = acc_result.scalars().all()
                
                for account in accounts:
                    try:
                        credentials = decrypt_data(account.credentials_encrypted)
                        credentials["environment"] = account.environment
                        await cls.reconcile_single_account(account, db, credentials)
                        total_synced += 1
                    except Exception as e:
                        logger.error(f"🧹 [Janitor] Failed to reconcile account {account.id} ({account.broker_name}): {e}")

        logger.info(f"🧹 [Janitor] Reconciliation cycle complete. Synced {total_synced} accounts.")

    @classmethod
    async def reconcile_single_account(cls, account: BrokerAccount, db: AsyncSession, credentials: Dict[str, Any]):
        """
        Sync a single account with local DB (Broker Agnostic).
        """
        logger.info(f"🧹 [Janitor] Reconciling {account.broker_name} account {account.account_name} ({account.account_number})")
        
        # 1. Fetch live trades from Broker via Adapter
        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        
        # All adapters MUST support get_open_trades() as part of the interface
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
        desync_count = 0
        for o_trade in olympus_trades:
            btid = o_trade.broker_trade_id
            
            if btid and str(btid) not in broker_trade_ids:
                logger.warning(f"⚠️ [Janitor] Desync Detected! {account.broker_name} Trade {o_trade.trade_id} (Broker: {btid}) is missing. Closing in Olympus.")
                
                # Mark as CLOSED in DB (effectively marking as historical/missing)
                o_trade.status = TradeStatus.CLOSED
                o_trade.exit_timestamp = datetime.utcnow()
                if not o_trade.metadata_json:
                    o_trade.metadata_json = {}
                o_trade.metadata_json['janitor_close'] = True
                o_trade.metadata_json['close_reason'] = f"CLOSED_EXTERNALLY_ON_{account.broker_name}_DETECTED_BY_JANITOR"
                desync_count += 1
                
        if desync_count > 0:
            await db.commit()
            logger.info(f"🧹 [Janitor] Processed {desync_count} desyncs for {account.account_name}.")
        else:
            logger.info(f"🧹 [Janitor] Account {account.account_name} is perfectly in sync.")
