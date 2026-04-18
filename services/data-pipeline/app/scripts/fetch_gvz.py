import yfinance as yf
import redis
import os
import json
import logging
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

async def fetch_gvz():
    """
    Fetch Gold Volatility Index (^GVZ) from yfinance and push to Redis.
    """
    try:
        logger.info("Fetching ^GVZ from yfinance...")
        gvz = yf.Ticker("^GVZ")
        # Get last 1 day of data
        hist = gvz.history(period="1d")
        
        if hist.empty:
            logger.warning("No GVZ data found.")
            return

        latest_value = float(hist['Close'].iloc[-1])
        timestamp = str(hist.index[-1])
        
        payload = {
            "symbol": "^GVZ",
            "value": latest_value,
            "timestamp": timestamp,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        r = redis.from_url(REDIS_URL)
        r.set("market_data:gvz", json.dumps(payload))
        logger.info(f"Successfully updated GVZ: {latest_value} at {timestamp}")
        
    except Exception as e:
        logger.error(f"Error fetching GVZ: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(fetch_gvz())
