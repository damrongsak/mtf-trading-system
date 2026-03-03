import json
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Fund, RiskFilter
from app.filters.base import BaseFilter
from app.utils.redis_client import get_redis_client
import logging

logger = logging.getLogger(__name__)

class QuantFilter(BaseFilter):
    def __init__(self):
        super().__init__("QUANT_FILTER")

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
            quant = context.get("quant", {})
            
            risk_score = quant.get("risk_score", 50)
            regime = quant.get("regime", "UNKNOWN")
            
            max_risk_score = filter_config.threshold_parameters.get("max_risk_score", 80)
            blocked_regimes = filter_config.threshold_parameters.get("blocked_regimes", [])
            
            if risk_score > max_risk_score:
                 raise ValueError(f"Risk Violation: Quant Risk Score too high ({risk_score} > {max_risk_score})")
                 
            if regime in blocked_regimes:
                 raise ValueError(f"Risk Violation: Trading blocked in Quant Regime: {regime}")
                 
        except json.JSONDecodeError:
            pass
            
        return True
