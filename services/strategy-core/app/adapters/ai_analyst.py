import httpx
import os
import logging

logger = logging.getLogger(__name__)

AI_ANALYST_URL = os.getenv("AI_ANALYST_URL", "http://ai-analyst:8000")

async def get_market_sentiment(symbol: str) -> dict:
    """
    Call AI Analyst to get sentiment score.
    Returns: {"score": float, "reason": str} or None on failure.
    """
    try:
        async with httpx.AsyncClient() as client:
            payload = {"symbol": symbol}
            response = await client.post(
                f"{AI_ANALYST_URL}/analyze/sentiment",
                json=payload,
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                return data # Expects {score: float, reason: str}
            else:
                logger.warning(f"AI Analyst Sentiment Check failed: {response.text}")
                return None
    except Exception as e:
        logger.error(f"Failed to connect to AI Analyst: {e}")
        return None
