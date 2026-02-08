from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class MarketStatusService:
    """Detects Forex market open/closed status"""
    
    FOREX_OPEN_HOUR_UTC = 22  # Sunday 22:00 UTC (Sydney open)
    FOREX_CLOSE_HOUR_UTC = 22  # Friday 22:00 UTC (NY close)
    
    async def get_market_status(self, symbol: str) -> Dict:
        """
        Returns market status for a given symbol
        
        Args:
            symbol: Trading symbol (e.g., XAUUSD, EURUSD)
        
        Returns:
            {
                "is_open": bool,
                "reason": str,
                "next_open": Optional[datetime],
                "next_close": Optional[datetime]
            }
        """
        now = datetime.now(timezone.utc)
        
        # Forex markets (XAU/USD, EUR/USD, etc.)
        if self._is_forex_symbol(symbol):
            return self._get_forex_status(now)
        
        # Crypto markets (24/7)
        elif self._is_crypto_symbol(symbol):
            return {
                "is_open": True,
                "reason": "Crypto markets trade 24/7",
                "next_open": None,
                "next_close": None
            }
        
        # Default: assume closed
        return {
            "is_open": False,
            "reason": "Unknown market type",
            "next_open": None,
            "next_close": None
        }
    
    def _get_forex_status(self, now: datetime) -> Dict:
        """Check if Forex market is open (24/5 trading)"""
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        hour = now.hour
        
        # Saturday: Closed all day
        if weekday == 5:
            next_open = self._next_sunday_22utc(now)
            return {
                "is_open": False,
                "reason": "Weekend: Forex markets closed",
                "next_open": next_open,
                "next_close": None
            }
        
        # Sunday: Open from 22:00 UTC
        if weekday == 6:
            if hour >= 22:
                next_close = self._next_friday_22utc(now)
                return {
                    "is_open": True,
                    "reason": "Forex markets open",
                    "next_open": None,
                    "next_close": next_close
                }
            else:
                next_open = now.replace(hour=22, minute=0, second=0, microsecond=0)
                return {
                    "is_open": False,
                    "reason": "Weekend: Markets open Sunday 22:00 UTC",
                    "next_open": next_open,
                    "next_close": None
                }
        
        # Friday: Close at 22:00 UTC
        if weekday == 4 and hour >= 22:
            next_open = self._next_sunday_22utc(now)
            return {
                "is_open": False,
                "reason": "Weekend: Markets closed Friday 22:00 UTC",
                "next_open": next_open,
                "next_close": None
            }
        
        # Monday-Friday (before 22:00): Open
        next_close = self._next_friday_22utc(now)
        return {
            "is_open": True,
            "reason": "Forex markets open",
            "next_open": None,
            "next_close": next_close
        }
    
    def _is_forex_symbol(self, symbol: str) -> bool:
        """Check if symbol is a Forex pair"""
        forex_pairs = ["XAU", "EUR", "GBP", "USD", "JPY", "AUD", "NZD", "CAD", "CHF"]
        return any(pair in symbol.upper() for pair in forex_pairs)
    
    def _is_crypto_symbol(self, symbol: str) -> bool:
        """Check if symbol is a cryptocurrency"""
        crypto = ["BTC", "ETH", "SOL", "USDT", "USDC"]
        return any(c in symbol.upper() for c in crypto)
    
    def _next_sunday_22utc(self, now: datetime) -> datetime:
        """Calculate next Sunday 22:00 UTC"""
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0 and now.hour >= 22:
            days_until_sunday = 7
        
        next_sunday = now + timedelta(days=days_until_sunday)
        return next_sunday.replace(hour=22, minute=0, second=0, microsecond=0)
    
    def _next_friday_22utc(self, now: datetime) -> datetime:
        """Calculate next Friday 22:00 UTC"""
        days_until_friday = (4 - now.weekday()) % 7
        if days_until_friday == 0 and now.hour >= 22:
            days_until_friday = 7
        
        next_friday = now + timedelta(days=days_until_friday)
        return next_friday.replace(hour=22, minute=0, second=0, microsecond=0)
