import logging
from app.core.globals import services

logger = logging.getLogger("ai-analyst.tasks")

async def update_gold_sentiment():
    """
    Scheduled task to refresh XAUUSD sentiment score.
    """
    logger.info("🔄 Running Scheduled Sentiment Update for XAUUSD...")
    
    sentiment_service = services.get("sentiment")
    if not sentiment_service:
        logger.error("❌ Sentiment Service not available in globals.")
        return

    try:
        # Defaults to XAUUSD after standardization
        result = await sentiment_service.get_sentiment(symbol="XAUUSD")
        logger.info(f"✅ Sentiment Update Complete for XAUUSD: {result.get('score')} ({result.get('reason')})")
    except Exception as e:
        logger.error(f"❌ Sentiment Update Failed: {e}")
