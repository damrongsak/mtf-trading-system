import yfinance as yf
import logging
from typing import Dict, Any, Optional
import json
import asyncio
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class YFinanceAdapter:
    """
    Adapter for Yahoo Finance to fetch macro indicators.
    """
    
    # Symbols: DX-Y.NYB (DXY), ^VIX (Volatility Index), ^GVZ (Gold Volatility Index)
    MACRO_SYMBOLS = {
        "DXY": "DX-Y.NYB",
        "VIX": "^VIX",
        "GVZ": "^GVZ"
    }

    async def fetch_indicator(self, label: str) -> Optional[Dict[str, Any]]:
        """
        Fetches the latest data for a macro indicator.
        """
        yf_symbol = self.MACRO_SYMBOLS.get(label)
        if not yf_symbol:
            return None
            
        try:
            # yfinance is blocking, so run in thread
            ticker = yf.Ticker(yf_symbol)
            hist = await asyncio.to_thread(ticker.history, period="1d")
            
            if hist.empty:
                logger.warning(f"No {label} data found from yfinance.")
                return None

            latest_value = float(hist['Close'].iloc[-1])
            timestamp = str(hist.index[-1].isoformat())
            
            return {
                "symbol": yf_symbol,
                "value": latest_value,
                "timestamp": timestamp,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching {label} ({yf_symbol}) from yfinance: {e}")
            return None

    async def sync_all_macro(self, publisher: Any) -> Dict[str, float]:
        """
        Syncs all macro indicators to Redis.
        """
        results = {}
        
        for label in self.MACRO_SYMBOLS.keys():
            data = await self.fetch_indicator(label)
            if data:
                # 1. Update individual key for HFT-lite O(1) reads
                key = f"macro:{label.lower()}"
                await publisher.redis.set(key, str(data["value"]))
                
                # 2. Update rich JSON key for broad consumption
                rich_key = f"market_data:{label.lower()}"
                await publisher.redis.set(rich_key, json.dumps(data))
                
                results[label] = data["value"]
                
        if results:
            # Broadcast to system
            await publisher.publish("system:macro_update", results)
            logger.info(f"Macro Sync Complete: {results}")
            
        return results

# Singleton
yfinance_adapter = YFinanceAdapter()
