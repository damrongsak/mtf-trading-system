import json
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Fund, RiskFilter
from app.filters.base import BaseFilter
from app.utils.redis_client import get_redis_client
import logging

logger = logging.getLogger(__name__)

class LiquidityFilter(BaseFilter):
    def __init__(self):
        super().__init__("LIQUIDITY_FILTER")

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
            return True
            
        try:
            context = json.loads(raw_val)
            liquidity = context.get("liquidity", {})
            gamma_regime = liquidity.get("regime", "UNKNOWN")
            
            blocked_gamma_regimes = filter_config.threshold_parameters.get("blocked_gamma_regimes", [])
            
            if gamma_regime in blocked_gamma_regimes:
                 raise ValueError(f"Risk Violation: Trading blocked during Gamma Regime ({gamma_regime})")
                 
            # Could also compute distance to Max Pain or Call/Put Walls here
                 
        except json.JSONDecodeError:
            pass
            
        return True
