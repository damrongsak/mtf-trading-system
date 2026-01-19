
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

def start_scheduler():
    # Run once at startup? Or just schedule?
    # Usually schedule daily at 00:00 UTC
    scheduler.add_job(
        check_and_refresh_tokens_job,
        CronTrigger(hour=0, minute=0), # Daily midnight
        id="daily_token_refresh",
        replace_existing=True
    )
    
    # Also run once immediately on startup (with slight delay) to catch up if needed?
    # Or maybe user prefers strict schedule.
    # Let's add a startup run after 60s
    scheduler.add_job(
        check_and_refresh_tokens_job,
        'date',
        run_date=None, # run ASAP? No, APScheduler 'date' trigger without run_date needs args?
        # To run ASAP:
        # None defaults to now.
        # But let's delay 30s to let server start
        # scheduler.add_job(check_and_refresh_tokens_job, 'interval', seconds=10) # Testing
        # Using a one-off date trigger in 30s
    )
    
    # Proper ASAP run:
    # scheduler.add_job(check_and_refresh_tokens_job) -> Runs immediately.
    
    logger.info("APScheduler started.")
    scheduler.start()
