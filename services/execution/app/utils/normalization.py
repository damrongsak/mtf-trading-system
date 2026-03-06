import logging
from datetime import datetime, timezone
from typing import Union, Optional

logger = logging.getLogger(__name__)

def parse_iso_timestamp(ts: Union[str, int, float, datetime]) -> datetime:
    """
    Normalizes various timestamp formats into a timezone-aware UTC datetime.
    Supports: ISO strings, Unix timestamps (ms/s), and datetime objects.
    """
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    
    if isinstance(ts, (int, float)):
        # Guess if it's ms or s
        if ts > 1e11: # Milliseconds
            return datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    
    if isinstance(ts, str):
        try:
            # Handle OANDA/ISO formats: "2016-06-22T18:41:35.433291884Z"
            # Strip nanoseconds if present (Python strptime handles up to microseconds)
            if "Z" in ts:
                ts = ts.replace("Z", "+00:00")
            
            # Simple ISO parse
            return datetime.fromisoformat(ts).astimezone(timezone.utc)
        except Exception as e:
            logger.warning(f"Normalization: Failed to parse timestamp {ts}: {e}")
            return datetime.now(timezone.utc)

    return datetime.now(timezone.utc)

def units_to_standard_lots(units: float) -> float:
    """
    Converts raw units into 'Standard Lots' (where 1.0 = 100,000 units).
    """
    return round(float(units) / 100000.0, 4)

def calculate_pnl_percentage(entry: float, exit: float, direction: str) -> float:
    """
    Calculates ROI/PnL percentage based on price movement.
    """
    if not entry or entry == 0:
        return 0.0
    
    if direction.upper() in ["LONG", "BUY"]:
        return ((exit - entry) / entry) * 100.0
    else:
        return ((entry - exit) / entry) * 100.0
