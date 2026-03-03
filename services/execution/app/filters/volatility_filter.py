import json
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Fund, RiskFilter
from app.filters.base import BaseFilter
from app.utils.redis_client import get_redis_client
import logging

logger = logging.getLogger(__name__)

class VolatilityFilter(BaseFilter):
    def __init__(self):
        super().__init__("VOLATILITY_FILTER")

    async def validate(
        self,
        db: AsyncSession,
        adapter: Any,
        fund: Fund,
        symbol: str,
        direction: str,
        sl_price: float,
        tp_price: float,
        entry_price: float,
        filter_config: RiskFilter
    ) -> bool:
        redis = get_redis_client()
        key = f"mtf:market_context:{symbol}"
        
        raw_val = await redis.get(key)
        if not raw_val:
            logger.warning(f"VolatilityFilter: No context found for {symbol} in Redis. Passing by default.")
            return True
            
        try:
            context = json.loads(raw_val)
            piv_volatility = context.get("piv", {}).get("volatility", 0.0)
            
            # Check DB configured threshold
            max_volatility = filter_config.threshold_parameters.get("max_piv_volatility", 0.0)
            
            if max_volatility > 0 and piv_volatility > max_volatility:
                 raise ValueError(f"Risk Violation: PIV Volatility too high ({piv_volatility:.4f} > {max_volatility}). Market too dangerous.")
                 
        except json.JSONDecodeError:
            logger.error(f"Failed to parse market context from Redis for {symbol}")
            
        return True
