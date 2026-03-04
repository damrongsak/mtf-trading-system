import logging
import json
import time
import os
from typing import Optional, Dict, Tuple
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

class PriceService:
    """
    Sub-millisecond Price Service:
    - Direct Redis Hash lookup (L2)
    - In-memory Pub/Sub stream caching (L1 - Future)
    - Stale Price Detection (Safety Guard)
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PriceService, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.redis = None
        self.initialized = True

    async def _get_redis(self):
        if not self.redis:
            self.redis = aioredis.from_url(self.redis_url, decode_responses=True)
        return self.redis

    async def get_latest_price(self, symbol: str, max_age_ms: int = 500) -> Tuple[Optional[float], Optional[str]]:
        """
        Fetches the latest price from the Redis-backed ECST cache.
        Returns: (price, error_message)
        """
        norm_symbol = symbol.replace("_", "").replace("/", "").upper()
        key = f"market_data:spot:{norm_symbol}"
        
        try:
            r = await self._get_redis()
            data = await r.hgetall(key)
            
            if not data or "bid" not in data:
                return None, f"No price data found for {symbol} in cache"
            
            # Stale Check
            ts = float(data.get("ts", 0))
            now = time.time()
            age_ms = (now - ts) * 1000
            
            if age_ms > max_age_ms:
                logger.warning(f"⚠️ Stale Price detected for {symbol}: {age_ms:.0f}ms old")
                return None, f"Price stale ({age_ms:.0f}ms > {max_age_ms}ms)"
            
            # For execution, we typically use the Mid price or Bid/Ask depending on direction
            # Defaulting to midpoint for risk calculation
            bid = float(data["bid"])
            ask = float(data["ask"])
            mid = (bid + ask) / 2
            
            return mid, None
            
        except Exception as e:
            logger.error(f"PriceService Error: {e}")
            return None, str(e)

price_service = PriceService()
