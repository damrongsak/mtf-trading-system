
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
import asyncio
from app.database import SessionLocal
from app.models.broker_account import BrokerAccount
from app.services.auth_service import refresh_ctrader_token_internal

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

def start_scheduler():
    # ... existing jobs ...
    scheduler.add_job(
        check_and_refresh_tokens_job,
        CronTrigger(hour=0, minute=0), # Daily midnight
        id="daily_token_refresh",
        replace_existing=True
    )
    
    # Schedule Log Cleanup every hour
    scheduler.add_job(
        cleanup_strategy_logs_job,
        IntervalTrigger(hours=1),
        id="strategy_log_cleanup",
        replace_existing=True
    )

    logger.info("APScheduler started.")
    scheduler.start()
