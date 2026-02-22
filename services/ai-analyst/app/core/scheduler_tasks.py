import logging
from app.core.globals import services

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
