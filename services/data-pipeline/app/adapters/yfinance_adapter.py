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
        Fetches the latest value for a macro indicator.
        """
        ticker_symbol = self.MACRO_SYMBOLS.get(label)
        if not ticker_symbol:
            return None
            
        try:
            logger.info(f"YFinance: Fetching indicator {label} ({ticker_symbol})")
            ticker = yf.Ticker(ticker_symbol)
            # Fetch last 5 days to ensure we get at least one close (weekends)
            df = await asyncio.to_thread(ticker.history, period="5d", interval="1d")
            
            if df.empty:
                logger.warning(f"YFinance: No indicator data for {label}")
                return None
                
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2] if len(df) > 1 else last_row
            
            value = float(last_row["Close"])
            prev_value = float(prev_row["Close"])
            change = value - prev_value
            change_pct = (change / prev_value * 100) if prev_value != 0 else 0
            
            data = {
                "symbol": label,
                "ticker": ticker_symbol,
                "value": round(value, 4),
                "change": round(change, 4),
                "change_pct": round(change_pct, 4),
                "timestamp": df.index[-1].to_pydatetime().isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            return data
        except Exception as e:
            logger.error(f"YFinance indicator error for {label}: {e}")
            return None

    async def fetch_candles(
        self, 
        ticker_symbol: str, 
        interval: str = "1h", 
        period: str = "60d",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> list[Dict[str, Any]]:
        """
        Fetches historical OHLC candles from Yahoo Finance.
        Args:
            ticker_symbol: YF ticker (e.g. ^GSPC, GC=F)
            interval: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
            period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
            start_date: Start datetime object
            end_date: End datetime object
        """
        try:
            ticker = yf.Ticker(ticker_symbol)
            
            # Prepare arguments for history()
            kwargs = {"interval": interval}
            if start_date and end_date:
                kwargs["start"] = start_date.strftime("%Y-%m-%d")
                kwargs["end"] = end_date.strftime("%Y-%m-%d")
            else:
                kwargs["period"] = period

            logger.info(f"YFinance: Fetching {ticker_symbol} | Interval: {interval} | Range: {kwargs.get('start', 'N/A')} - {kwargs.get('end', 'N/A')}")
            
            df = await asyncio.to_thread(ticker.history, **kwargs)
            
            if df.empty:
                logger.warning(f"YFinance: No data returned for {ticker_symbol}")
                return []

            candles = []
            for ts, row in df.iterrows():
                candles.append({
                    "timestamp": ts.to_pydatetime() if hasattr(ts, 'to_pydatetime') else ts,
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                })
            
            return candles
        except Exception as e:
            logger.error(f"YFinance error for {ticker_symbol}: {e}")
            return []

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
