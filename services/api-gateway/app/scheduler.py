
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
import asyncio
from app.database import SessionLocal
from app.models.broker_account import BrokerAccount
from app.services.auth_service import refresh_ctrader_token_internal
from app.utils.scheduler_utils import with_tracing

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def check_and_refresh_tokens_job():
    """
    Background job to check cTrader accounts for expiring tokens.
    """
    logger.info("Starting Daily Token Refresh Check...")
    db = SessionLocal()
    try:
        accounts = db.query(BrokerAccount).filter(
            BrokerAccount.broker_name == "CTRADER",
            BrokerAccount.is_active == True
        ).all()
        
        refreshed_count = 0
        total_count = len(accounts)
        
        for account in accounts:
            # We call internal service which handles checks
            # Note: The service currently only logs if skipping.
            # We need to ensure it checks 'expires_at'. 
            # Yes, refresh_ctrader_token_internal logic:
            # - decrypt
            # - if force=False: check expires_at > 3 days -> skip
            # - else -> post to data-pipeline -> update DB
            
            try:
                result = await refresh_ctrader_token_internal(account, db, force=False)
                if result:
                    refreshed_count += 1
            except Exception as e:
                logger.error(f"Error checking account {account.id}: {e}")
                
        logger.info(f"Token Refresh Check Complete. Refreshed {refreshed_count}/{total_count} accounts.")
        
    except Exception as e:
        logger.error(f"Token Refresh Job Failed: {e}")
    finally:
        db.close()


async def cleanup_strategy_logs_job():
    """
    Deletes strategy execution logs older than 6 hours.
    """
    logger.info("Starting Strategy Log Cleanup...")
    db = SessionLocal()
    try:
        from app.models.strategy_execution_log import StrategyExecutionLog
        from datetime import datetime, timedelta
        
        cutoff = datetime.now() - timedelta(hours=6)
        deleted = db.query(StrategyExecutionLog).filter(
            StrategyExecutionLog.timestamp < cutoff
        ).delete(synchronize_session=False)
        
        db.commit()
        logger.info(f"Cleaned up {deleted} strategy execution logs.")
    except Exception as e:
        logger.error(f"Strategy Log Cleanup Failed: {e}")
    finally:
        db.close()


async def auto_load_trades_to_journal_job():
    """
    Automatically creates draft JournalEntry records for closed trades.
    Runs every 5 minutes.
    """
    logger.info("Starting Auto-Load Trades to Journal Job...")
    db = SessionLocal()
    try:
        from app.models.trade import Trade
        from app.models.journal import JournalEntry
        from sqlalchemy import and_
        
        # 1. Fetch CLOSED trades that do not have a corresponding JournalEntry
        # trade_id is unique in journal_entries
        journal_subq = db.query(JournalEntry.trade_id).filter(JournalEntry.trade_id.isnot(None)).subquery()
        
        pending_trades = db.query(Trade).filter(
            and_(
                Trade.status.in_(["CLOSED", "REJECTED"]), # Also load rejected for review
                Trade.trade_id.notin_(journal_subq)
            )
        ).all()
        
        if not pending_trades:
            logger.info("No new closed trades found for journaling.")
            return
            
        added_count = 0
        for trade in pending_trades:
            # 2. Resolve user_id (Consistency with journal internal API)
            user_id = None
            if hasattr(trade, 'broker_account_id') and trade.broker_account_id:
                from app.models.broker_account import BrokerAccount
                account = db.query(BrokerAccount).filter(BrokerAccount.id == trade.broker_account_id).first()
                if account and hasattr(account, 'fund_id') and account.fund_id:
                    from app.models.user_fund import UserFund
                    uf = db.query(UserFund).filter(UserFund.fund_id == account.fund_id).first()
                    if uf:
                        user_id = uf.user_id

            # Fallback to the first system user if resolution fails
            if not user_id:
                from app.models.user import User
                first_user = db.query(User).first()
                if first_user:
                    user_id = first_user.id
            
            if not user_id:
                logger.warning(f"Could not resolve user_id for trade {trade.trade_id}. Skipping auto-load.")
                continue
                
            # 3. Create Draft Journal Entry
            new_entry = JournalEntry(
                user_id=user_id,
                trade_id=trade.trade_id,
                symbol=trade.symbol,
                direction=trade.direction.value if hasattr(trade.direction, 'value') else str(trade.direction),
                entry_price=float(trade.entry_price) if trade.entry_price else None,
                exit_price=float(trade.exit_price) if trade.exit_price else None,
                pnl_amount=float(trade.pnl_usd) if trade.pnl_usd else None,
                session="Auto-Load",
                is_ai_generated=False # This is a human/draft entry
            )
            db.add(new_entry)
            added_count += 1
            
        db.commit()
        logger.info(f"Auto-Load Complete: Created {added_count} draft journal entries.")
        
    except Exception as e:
        logger.error(f"Auto-Load Trades Job Failed: {e}")
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(
        with_tracing(check_and_refresh_tokens_job),
        CronTrigger(hour=0, minute=0), # Daily midnight
        id="daily_token_refresh",
        replace_existing=True
    )
    
    # Schedule Log Cleanup every hour
    scheduler.add_job(
        with_tracing(cleanup_strategy_logs_job),
        IntervalTrigger(hours=1),
        id="strategy_log_cleanup",
        replace_existing=True
    )
    
    # Schedule Auto-Load Journal every 5 minutes
    scheduler.add_job(
        with_tracing(auto_load_trades_to_journal_job),
        IntervalTrigger(minutes=5),
        id="auto_load_journal",
        misfire_grace_time=30, # Allow 30 seconds of lag
        replace_existing=True
    )

    logger.info("APScheduler started.")
    scheduler.start()
