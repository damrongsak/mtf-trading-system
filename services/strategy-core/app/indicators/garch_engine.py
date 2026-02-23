import pandas as pd
import numpy as np
import redis
import pickle
import os
import hashlib
import logging
from typing import Optional, Tuple
from arch import arch_model

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

class GARCHEngine:
    def __init__(self):
        self.redis = redis.from_url(REDIS_URL)
        self.cache_ttl = 3600  # 1 hour

    def _get_cache_key(self, returns: pd.Series, model_type: str = "GJR-GARCH") -> str:
        """
        Generate a unique cache key based on the data hash and model type.
        """
        data_hash = hashlib.md5(pd.util.hash_pandas_object(returns).values).hexdigest()
        return f"garch_cache:{model_type}:{data_hash}"

    def get_volatility_forecast(self, returns: pd.Series, horizon: int = 5) -> Tuple[float, bool]:
        """
        Get GJR-GARCH(1,1) volatility forecast.
        Checks Redis cache first.
        Returns: (forecasted_vol, is_from_cache)
        """
        # Clean returns
        returns = returns.dropna() * 100 # Scale for stability in arch
        if len(returns) < 100:
            logger.warning("Insufficient data for GARCH fit (< 100 periods).")
            return 0.0, False

        cache_key = self._get_cache_key(returns)
        cached_val = self.redis.get(cache_key)
        
        if cached_val:
            logger.debug(f"GARCH Cache Hit: {cache_key}")
            return float(cached_val), True

        try:
            # GJR-GARCH(1,1) with Skewed Student's t-distribution
            # p=1 (GARCH), q=1 (ARCH), o=1 (Asymmetry/GJR)
            model = arch_model(returns, p=1, q=1, o=1, vol='Garch', dist='skewt')
            res = model.fit(disp='off', show_warning=False)
            
            # Forecast next 'horizon' periods
            forecast = res.forecast(horizon=horizon)
            # Annualized volatility forecast (assuming H1 or M15, but we keep raw for PIV)
            # We take the sqrt of the variance of the last step
            forecasted_variance = forecast.variance.values[-1, -1]
            forecasted_vol = np.sqrt(forecasted_variance) / 100.0 # Rescale back
            
            # Cache the result
            self.redis.setex(cache_key, self.cache_ttl, str(forecasted_vol))
            logger.info(f"GARCH Cache Miss. New Forecast: {forecasted_vol:.4f}")
            
            return forecasted_vol, False
            
        except Exception as e:
            logger.error(f"GARCH Fit Error: {e}")
            return 0.0, False

    def get_projected_volatility(self, returns: pd.Series) -> float:
        """
        PIV Logic: Retrieve GVZ from Redis, or fallback to GJR-GARCH realized forecast.
        """
        # Try to get GVZ from Data Pipeline
        gvz_data = self.redis.get("market_data:gvz")
        
        if gvz_data:
            try:
                import json
                parsed = json.loads(gvz_data)
                gvz_val = parsed.get("value")
                if gvz_val:
                    logger.debug(f"Using Live GVZ: {gvz_val}")
                    return float(gvz_val)
            except Exception as e:
                logger.warning(f"Failed to parse GVZ from Redis: {e}")

        # Fallback to local GARCH Realized Volatility forecast
        logger.info("GVZ Unavailable. Falling back to GJR-GARCH Realized Volatility.")
        forecast, _ = self.get_volatility_forecast(returns)
        
        # Scale realized vol (e.g. 0.005) to a GVZ-like index (e.g. 15.0)
        # GVZ ~ Annualized Vol. 
        # For M15 data, we'd multiply by sqrt(100 * 252 * 96) or similar.
        # But PIV N-Bands logic uses (multiplier * ATR * (1 + GVZ/100))
        # If we use GARCH vol directly, we should adjust the multiplier in strategy.
        # For consistency, let's normalize GARCH vol to a 'Volatility Index' percentage.
        
        return forecast * 1000.0 # Heuristic scaling to match GVZ magnitude (~10-30)

garch_engine = GARCHEngine()
