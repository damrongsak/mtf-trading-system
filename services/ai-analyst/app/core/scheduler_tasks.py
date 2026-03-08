import logging
from decimal import Decimal
import uuid
from app.core.globals import services
from app.database import SessionLocal
from sqlalchemy import text
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("ai-analyst.tasks")

async def update_gold_sentiment():
    """
    Scheduled task to refresh XAUUSD sentiment score.
    Uses smarter caching and robust fallbacks.
    """
    logger.info("🔄 Running Scheduled Sentiment Update for XAUUSD...")
    
    sentiment_service = services.get("sentiment")
    if not sentiment_service:
        logger.error("❌ Sentiment Service not available in globals. Check lifespan startup.")
        return

    try:
        # Defaults to XAUUSD
        # The service now uses gemini-2.5-flash and headline hashing
        result = await sentiment_service.get_sentiment(symbol="XAUUSD")
        
        score = result.get('score', 0.0)
        reason = result.get('reason', 'No reason provided')
        
        if score == 0.0 and "Error" in reason:
            logger.warning(f"⚠️ Sentiment update returned fallback value: {reason}")
        else:
            logger.info(f"✅ Sentiment Update Success: {score} | {reason}")
            
    except Exception as e:
        logger.error(f"❌ Critical Failure in update_gold_sentiment task: {e}")

async def run_daily_post_mortem():
    """
    Scheduled task to analyze closed trades from the last 24 hours.
    Extracts lessons learned and stores them in Qdrant.
    """
    logger.info("🔄 Running Daily Post-Mortem Analysis...")
    
    agent = services.get("post_mortem")
    if not agent:
        logger.error("❌ PostMortemAgent not available in globals.")
        return

    db = SessionLocal()
    try:
        # Fetch closed trades from last 24h
        # Since we don't have the full models here, we use raw SQL or a minimal Reflected model
        # Using raw SQL is safer to avoid importing models from other services
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        
        query = text("""
            SELECT trade_id as id, symbol, entry_price, exit_price, pnl_usd as result_pnl, 
                   status, direction, strategy_name, exit_timestamp
            FROM trades
            WHERE status = 'CLOSED' AND exit_timestamp >= :yesterday
        """)
        
        result = db.execute(query, {"yesterday": yesterday}).mappings().all()
        # Convert SQLAlchemy RowMappings to standard dicts
        # The PostMortemAgent.safe_json_dumps handles UUID, Decimal, and datetime
        trades = [dict(r) for r in result]
        
        if not trades:
            logger.info("ℹ️ No closed trades found in the last 24 hours. Skipping analysis.")
            return

        logger.info(f"📊 Analyzing {len(trades)} trades for post-mortem...")
        
        # We assume a default user for daily cron or iterate over users
        # For now, using 'trader1' as default if not specified
        user_id = "trader1" 
        
        results = await agent.run_batch_analysis(trades, user_id)
        logger.info(f"✅ Daily Post-Mortem complete. {len(results)} lessons processed.")
            
    except Exception as e:
        logger.error(f"❌ Critical Failure in run_daily_post_mortem task: {e}")
    finally:
        db.close()
