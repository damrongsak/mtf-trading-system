from datetime import datetime, timedelta, timezone
from typing import Any
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Fund, RiskFilter, EconomicEvent
from app.filters.base import BaseFilter
import logging

logger = logging.getLogger(__name__)

class NewsFilter(BaseFilter):
    def __init__(self):
        super().__init__("NEWS_FILTER")

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
        
        # Determine check window, default +/- 30m
        minutes_before = filter_config.threshold_parameters.get("minutes_before", 30)
        minutes_after = filter_config.threshold_parameters.get("minutes_after", 30)
        
        window_start = now - timedelta(minutes=minutes_after)
        window_end = now + timedelta(minutes=minutes_before)
        
        # Base currency mapping (e.g. XAUUSD -> USD, EURUSD -> EUR, USD)
        currencies = []
        if "USD" in symbol: currencies.append("USD")
        if "EUR" in symbol: currencies.append("EUR")
        if "GBP" in symbol: currencies.append("GBP")
        if "JPY" in symbol: currencies.append("JPY")
        if not currencies:
            return True # Not a fiat cross we care about
            
        stmt = select(EconomicEvent).where(
            EconomicEvent.currency.in_(currencies),
            EconomicEvent.impact == "High",
            EconomicEvent.datetime >= window_start,
            EconomicEvent.datetime <= window_end
        )
        result = await db.execute(stmt)
        events = result.scalars().all()
        
        if events:
            event_titles = [e.title for e in events]
            raise ValueError(f"Risk Violation: High Impact News window. Detected: {', '.join(event_titles)}")
            
        return True
