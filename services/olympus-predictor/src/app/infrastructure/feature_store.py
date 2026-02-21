import json
import logging
import pandas as pd
import redis.asyncio as redis
from typing import Optional, Any
from src.app.core.config import settings

logger = logging.getLogger("olympus-predictor.infrastructure.feature_store")

class FeatureStore:
    """
    Redis-based Feature Store for MTF Olympus.
    Caches technical indicators, GARCH volatility, and market regimes.
    """
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.ttl = 86400 # 24 hours default cache

    async def get_features(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Retrieve cached features for a symbol/timeframe"""
        key = f"features:{symbol}:{timeframe}"
        data_json = await self.redis.get(key)
        if not data_json:
            return None
        
        try:
            # We use orient="split" for better serialization of DataFrames
            df = pd.read_json(data_json, orient="split")
            logger.debug(f"Cache hit for {key}")
            return df
        except Exception as e:
            logger.warning(f"Failed to parse cached features for {key}: {e}")
            return None

    async def save_features(self, symbol: str, timeframe: str, df: pd.DataFrame):
        """Cache features in Redis"""
        key = f"features:{symbol}:{timeframe}"
        try:
            data_json = df.to_json(orient="split")
            await self.redis.set(key, data_json, ex=self.ttl)
            logger.info(f"Cached features for {key} (Shape: {df.shape})")
        except Exception as e:
            logger.error(f"Failed to cache features for {key}: {e}")

    async def get_regime(self, symbol: str) -> Optional[int]:
        """Get latest market regime"""
        key = f"regime:{symbol}:latest"
        res = await self.redis.get(key)
        return int(res) if res is not None else None

    async def save_regime(self, symbol: str, regime: int):
        """Save latest market regime"""
        key = f"regime:{symbol}:latest"
        await self.redis.set(key, regime, ex=3600) # 1 hour TTL for regime
