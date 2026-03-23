import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, List

from app.filters.base import BaseFilter
from app.models import Fund, RiskFilter
from app.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class NewsFilter(BaseFilter):
    """
    [INSTITUTIONAL] Layer 4 News Filter.
    Checks for High Impact economic events in Redis (cached by data-pipeline).
    Rule 7 Compliance: DB-Free Hot Path.
    """
    def __init__(self):
        super().__init__("NEWS_FILTER")

    async def validate(
        self,
        db: Any,  # Kept for interface compatibility, but unused to remain DB-free
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
        symbol_upper = symbol.upper()
        
        # Major Currencies
        for curr in ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"]:
            if curr in symbol_upper:
                currencies.append(curr)
        
        # Gold specials
        if "XAU" in symbol_upper:
            if "USD" not in currencies:
                currencies.append("USD")
        
        if not currencies:
            return True # Not a currency/commodity cross we care about
            
        rc = get_redis_client()
        detected_events = []
        
        for currency in currencies:
            key = f"calendar:{currency}"
            cached_data = await rc.get(key)
            if not cached_data:
                continue
                
            try:
                events = json.loads(cached_data)
                for event in events:
                    # Logic: date-country-title-impact
                    # ForecastFactory (nfs) format usually has "date", "impact"
                    impact = event.get("impact", "Low")
                    if impact != "High":
                        continue
                        
                    event_dt_str = event.get("date")
                    if not event_dt_str:
                        continue
                        
                    try:
                        # Try to handle common formats
                        event_dt = datetime.fromisoformat(event_dt_str.replace('Z', '+00:00'))
                        # Ensure timezone aware if naive
                        if event_dt.tzinfo is None:
                            event_dt = event_dt.replace(tzinfo=timezone.utc)
                    except Exception:
                        logger.warning(f"Could not parse event date: {event_dt_str}")
                        continue
                        
                    if window_start <= event_dt <= window_end:
                        detected_events.append(f"{event.get('title')} ({currency})")
            except Exception as e:
                logger.error(f"Error parsing news cache for {currency}: {e}")
                continue

        if detected_events:
            msg = f"Risk Violation: High Impact News window. Detected: {', '.join(detected_events)}"
            logger.warning(f"🛑 {msg}")
            raise ValueError(msg)
            
        return True
