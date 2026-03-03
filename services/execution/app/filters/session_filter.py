from datetime import datetime, timezone
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Fund, RiskFilter
from app.filters.base import BaseFilter
import logging

logger = logging.getLogger(__name__)

class SessionFilter(BaseFilter):
    def __init__(self):
        super().__init__("SESSION_FILTER")

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
        now = datetime.now(timezone.utc)
        
        # Example: Skip 21:55 - 22:05 UTC (Rollover)
        if now.hour == 21 and 55 <= now.minute <= 59:
             raise ValueError("Risk Violation: Trading disabled during rollover (21:55 - 22:00 UTC)")
        if now.hour == 22 and 0 <= now.minute <= 5:
             raise ValueError("Risk Violation: Trading disabled during rollover window (22:00 - 22:05 UTC)")
             
        # Extract custom parameters from DB if any
        # blocked_hours = filter_config.threshold_parameters.get("blocked_hours", [])
        # if now.hour in blocked_hours: ...
        
        return True
