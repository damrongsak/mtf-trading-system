
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
    
    def get_active_ctrader_accounts():
        db = SessionLocal()
        try:
            return db.query(BrokerAccount).filter(
                BrokerAccount.broker_name == "CTRADER",
                BrokerAccount.is_active == True
            ).all()
        finally:
            db.close()

    try:
        accounts = await asyncio.to_thread(get_active_ctrader_accounts)
        
        refreshed_count = 0
        total_count = len(accounts)
        
        for account in accounts:
            try:
                # We need a new session for each refresh if it does DB updates
                # refresh_ctrader_token_internal takes a db session.
                # Let's run it in a way that handles its own session if possible, 
                # or provide one.
                
                async def refresh_with_session(acc):
                    db = SessionLocal()
                    try:
                        # refresh_ctrader_token_internal is async but contains sync DB calls.
                        # We still call it with await.
                        return await refresh_ctrader_token_internal(acc, db, force=False)
                    finally:
                        db.close()
                
                result = await refresh_with_session(account)
                if result:
                    refreshed_count += 1
            except Exception as e:
                logger.error(f"Error checking account {account.id}: {e}")
                
        logger.info(f"Token Refresh Check Complete. Refreshed {refreshed_count}/{total_count} accounts.")
        
    except Exception as e:
        logger.error(f"Token Refresh Job Failed: {e}")


async def cleanup_strategy_logs_job():
    """
    Deletes strategy execution logs older than 6 hours.
    """
    logger.info("Starting Strategy Log Cleanup...")
    
    def do_cleanup():
        db = SessionLocal()
        try:
            from app.models.strategy_execution_log import StrategyExecutionLog
            from datetime import datetime, timedelta
            
            cutoff = datetime.now() - timedelta(hours=6)
            deleted = db.query(StrategyExecutionLog).filter(
                StrategyExecutionLog.timestamp < cutoff
            ).delete(synchronize_session=False)
            
            db.commit()
            return deleted
        except Exception as e:
            logger.error(f"Strategy Log Cleanup DB Error: {e}")
            db.rollback()
            raise
        finally:
            db.close()

    try:
        deleted = await asyncio.to_thread(do_cleanup)
        logger.info(f"Cleaned up {deleted} strategy execution logs.")
    except Exception as e:
        logger.error(f"Strategy Log Cleanup Failed: {e}")


async def auto_load_trades_to_journal_job():
    """
    Automatically creates draft JournalEntry records for closed trades.
    Runs every 5 minutes.
    """
    logger.info("Starting Auto-Load Trades to Journal Job...")
    
    def do_auto_load():
        db = SessionLocal()
        try:
            from app.models.trade import Trade
            from app.models.journal import JournalEntry
            from sqlalchemy import and_
            
            # 1. Fetch CLOSED trades that do not have a corresponding JournalEntry
            journal_subq = db.query(JournalEntry.trade_id).filter(JournalEntry.trade_id.isnot(None)).subquery()
            
            pending_trades = db.query(Trade).filter(
                and_(
                    Trade.status.in_(["CLOSED", "REJECTED"]),
                    Trade.trade_id.notin_(journal_subq)
                )
            ).all()
            
            if not pending_trades:
                return 0
                
            added_count = 0
            for trade in pending_trades:
                # 2. Resolve user_id
                user_id = None
                if hasattr(trade, 'broker_account_id') and trade.broker_account_id:
                    from app.models.broker_account import BrokerAccount
                    account = db.query(BrokerAccount).filter(BrokerAccount.id == trade.broker_account_id).first()
                    if account and hasattr(account, 'fund_id') and account.fund_id:
                        from app.models.user_fund import UserFund
                        uf = db.query(UserFund).filter(UserFund.fund_id == account.fund_id).first()
                        if uf:
                            user_id = uf.user_id

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
                    is_ai_generated=False
                )
                db.add(new_entry)
                added_count += 1
                
            db.commit()
            return added_count
        except Exception as e:
            logger.error(f"Auto-Load DB Error: {e}")
            db.rollback()
            raise
        finally:
            db.close()

    try:
        added_count = await asyncio.to_thread(do_auto_load)
        if added_count > 0:
            logger.info(f"Auto-Load Complete: Created {added_count} draft journal entries.")
        else:
            logger.info("No new closed trades found for journaling.")
    except Exception as e:
        logger.error(f"Auto-Load Trades Job Failed: {e}")


async def check_price_alerts_job():
    """
    Background job to monitor price alerts and notify users via Telegram.
    Runs every minute.
    """
    logger.info("Checking Price Alerts...")
    db = SessionLocal()
    try:
        from app.models.alert import Alert, AlertCondition
        from app.models.candle import Candle
        from app.models.telegram_chat_mapping import TelegramChatMapping
        from sqlalchemy import func
        
        # 1. Fetch active, untriggered alerts
        active_alerts = db.query(Alert).filter(
            Alert.is_active == True,
            Alert.is_triggered == False
        ).all()
        
        if not active_alerts:
            return

        # 2. Group by symbol and get latest price for each symbol
        symbols = list(set(a.symbol for a in active_alerts))
        latest_prices = {}
        
        for symbol in symbols:
            # Get the latest candle across all timeframes (highest precision available)
            latest_candle = db.query(Candle).filter(
                Candle.symbol == symbol
            ).order_by(Candle.timestamp.desc()).first()
            
            if latest_candle:
                latest_prices[symbol] = float(latest_candle.close)

        # 3. Check conditions
        triggered_count = 0
        for alert in active_alerts:
            current_price = latest_prices.get(alert.symbol)
            if current_price is None:
                continue
            
            is_triggered = False
            if alert.condition == AlertCondition.PRICE_ABOVE:
                if current_price >= float(alert.threshold):
                    is_triggered = True
            elif alert.condition == AlertCondition.PRICE_BELOW:
                if current_price <= float(alert.threshold):
                    is_triggered = True
            
            if is_triggered:
                # MARK AS TRIGGERED IMMEDIATELY
                alert.is_triggered = True
                alert.is_active = False # Deactivate after trigger
                alert.last_triggered_at = func.now()
                db.add(alert)
                db.commit()
                
                # 4. Notify User via Telegram
                mapping = db.query(TelegramChatMapping).filter(
                    TelegramChatMapping.user_id == alert.user_id
                ).first()
                
                if mapping:
                    from app.routers.telegram import send_telegram_message
                    msg = (
                        f"🔔 *ALERT TRIGGERED*\n\n"
                        f"Asset: `{alert.symbol}`\n"
                        f"Condition: `{alert.condition.value}`\n"
                        f"Target: `{alert.threshold}`\n"
                        f"Current Price: `{current_price}`"
                    )
                    # Note: send_telegram_message is async
                    asyncio.create_task(send_telegram_message(mapping.chat_id, msg))
                    triggered_count += 1
                else:
                    logger.warning(f"Alert {alert.id} triggered but no Telegram mapping found for user {alert.user_id}")

        if triggered_count > 0:
            logger.info(f"Price Alerts: Triggered and notified {triggered_count} alerts.")
            
    except Exception as e:
        logger.error(f"Price Alert Job Failed: {e}")
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

    # Schedule Price Alert Monitoring every 1 minute
    scheduler.add_job(
        with_tracing(check_price_alerts_job),
        IntervalTrigger(minutes=1),
        id="price_alert_monitor",
        replace_existing=True
    )

    logger.info("APScheduler started.")
    scheduler.start()
