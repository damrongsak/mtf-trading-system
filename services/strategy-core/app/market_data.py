
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Deque
from datetime import datetime, timedelta
import threading
from collections import deque
import logging

logger = logging.getLogger(__name__)

class SymbolData:
    """
    Optimized Data Structure for a Single Symbol.
    Stores raw M1 candles in a circular buffer (deque) for O(1) updates.
    """
    def __init__(self, symbol: str, max_len: int = 5000):
        self.symbol = symbol
        self.lock = threading.RLock()
        
        # Base Timeframe: 1 Minute
        # Each element is dict: {timestamp, open, high, low, close, volume, delta}
        self.candles_m1: Deque[dict] = deque(maxlen=max_len)
        
        # Current forming candle state
        self.current_candle: Optional[dict] = None
        
        # EFP Spread Buffers
        self.efp_spreads: Deque[dict] = deque(maxlen=max_len)
        
        # Cache for recently requested DataFrames (Simple Memoization)
        # Key: timeframe, Value: (last_update_ts, DataFrame)
        self._df_cache: Dict[str, tuple] = {}

from app.database import SessionLocal
from app.models.candle import Candle
from sqlalchemy import select, desc

class SharedMarketDataManager:
    """
    High-Frequency Market Data Engine.
    Uses 'Buffer-First' architecture with Lazy DataFrame Synthesis.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SharedMarketDataManager, cls).__new__(cls)
                cls._instance.symbols: Dict[str, SymbolData] = {}
                cls._instance.global_lock = threading.RLock()
        return cls._instance

    def _get_symbol_data(self, symbol: str) -> SymbolData:
        """Get or Create SymbolData in a thread-safe way."""
        if symbol not in self.symbols:
            with self.global_lock:
                if symbol not in self.symbols:
                    self.symbols[symbol] = SymbolData(symbol)
        return self.symbols[symbol]

    def load_history(self, symbol: str, limit: int = 1000):
        """
        Hydrate buffer from Database (M1 Candles).
        Crucial for eliminating 'warmup' time.
        """
        s_data = self._get_symbol_data(symbol)
        
        with s_data.lock:
            if len(s_data.candles_m1) > 0:
                logger.info(f"Symbol {symbol} already has data, skipping hydration.")
                return

            logger.info(f"Hydrating {symbol} from DB (M1)...")
            db = SessionLocal()
            try:
                # Query M1 history
                stmt = select(Candle).where(
                    Candle.symbol == symbol,
                    Candle.timeframe == 'M1'
                ).order_by(desc(Candle.timestamp)).limit(limit)
                
                results = db.execute(stmt).scalars().all()
                
                if not results:
                    logger.warning(f"No M1 history found for {symbol} in DB.")
                    return

                # Convert to dicts and append (Reverse order because we fetched DESC)
                for c in reversed(results):
                    candle = {
                        'timestamp': c.timestamp.replace(tzinfo=None), # Normalize to naive if needed
                        'open': float(c.open),
                        'high': float(c.high),
                        'low': float(c.low),
                        'close': float(c.close),
                        'volume': float(c.volume)
                    }
                    s_data.candles_m1.append(candle)
                
                logger.info(f"Hydrated {symbol}: {len(results)} M1 candles loaded.")
                
            except Exception as e:
                logger.error(f"Hydration failed for {symbol}: {e}")
            finally:
                db.close()

    def update_tick(self, symbol: str, price: float, timestamp: datetime, bid: Optional[float] = None, ask: Optional[float] = None):
        """
        Ingest a tick in O(1).
        Updates the current M1 candle in-place.
        """
        # Ensure timestamp is TZ-naive or UTC normalized if needed
        # Assuming input is valid datetime
        
        s_data = self._get_symbol_data(symbol)
        
        with s_data.lock:
            # 1. Floor timestamp to M1
            ts_floor = timestamp.replace(second=0, microsecond=0)
            
            # 2. Rollover Check
            if s_data.current_candle and ts_floor > s_data.current_candle['timestamp']:
                # Commit completed candle to deque
                s_data.candles_m1.append(s_data.current_candle.copy())
                s_data.current_candle = None
                
                # Invalidate Caches because new H/L/C history exists
                s_data._df_cache.clear()

            # 3. Create or Update Envelope
            # Calculate Side/Delta (Primitive approximation without separate tick-stream)
            # Ideal: Pass side explicitly from caller if available.
            # Here we just treat volume=1 per tick.
            
            if s_data.current_candle is None:
                # New Candle
                s_data.current_candle = {
                    'timestamp': ts_floor,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': 1,
                    # 'delta': 0 # TODO: Implement delta logic if needed
                }
            else:
                # Update Existing
                c = s_data.current_candle
                c['high'] = max(c['high'], price)
                c['low'] = min(c['low'], price)
                c['close'] = price
                c['volume'] += 1

    def update_efp(self, symbol: str, spread: float, timestamp: float, raw_data: dict):
        """Update EFP spread for a symbol."""
        s_data = self._get_symbol_data(symbol)
        with s_data.lock:
            s_data.efp_spreads.append({
                't': timestamp,
                's': spread,
                'b': raw_data.get('b'),
                'a': raw_data.get('a'),
                'fb': raw_data.get('fb'),
                'fa': raw_data.get('fa')
            })

    def get_latest_efp(self, symbol: str) -> Optional[dict]:
        """Get latest EFP state."""
        s_data = self._get_symbol_data(symbol)
        with s_data.lock:
            if s_data.efp_spreads:
                return s_data.efp_spreads[-1]
            return None

    def get_data(self, symbol: str) -> pd.DataFrame:
        """
        Legacy Compatibility: Returns M1 DataFrame.
        Prefer get_candles(symbol, timeframe) for new strategies.
        """
        return self.get_candles(symbol, timeframe="1min")

    def get_candles(self, symbol: str, timeframe: str = "1min", limit: int = 1000) -> pd.DataFrame:
        """
        Standardized Accessor.
        Returns Pandas DataFrame [open, high, low, close, volume] indexed by timestamp.
        Lazy Resampling from M1 base.
        """
        s_data = self._get_symbol_data(symbol)
        
        with s_data.lock:
            # 1. Prepare Base M1 Data
            # Combine history + current incomplete candle for latest view
            data_source = list(s_data.candles_m1)
            if s_data.current_candle:
                data_source.append(s_data.current_candle)
            
            if not data_source:
                return pd.DataFrame()
            
            # 2. Check Cache (Optimization)
            # If requesting "1min" and we just built it, return copy
            # if timeframe == "1min" and ... (Skip for MVP, do raw construct)

            # 3. Construct DataFrame
            df = pd.DataFrame(data_source)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            # 4. Resample if needed
            if timeframe != "1min":
                try:
                    # Map common strings to Pandas offset aliases
                    # "1min" -> "1T", "5min" -> "5T", "1h" -> "1H"
                    tf_map = {
                        "1min": "1T", "5min": "5T", "15min": "15T", "30min": "30T",
                        "1h": "1H", "4h": "4H", "1d": "1D"
                    }
                    freq = tf_map.get(timeframe, timeframe)
                    
                    df_resampled = df.resample(freq).agg({
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last',
                        'volume': 'sum'
                    }).dropna()
                    
                    if limit:
                        return df_resampled.iloc[-limit:].copy()
                    return df_resampled
                    
                except Exception as e:
                    logger.error(f"Resampling error for {symbol} {timeframe}: {e}")
                    # Fallback to M1
                    return df.iloc[-limit:].copy() if limit else df.copy()

            if limit:
                return df.iloc[-limit:].copy()
            return df.copy()

    def set_data(self, symbol: str, df: pd.DataFrame):
        """
        Backfill/Seed Data.
        Replaces internal M1 buffer with data from DataFrame.
        Assumes DF is M1 data.
        """
        s_data = self._get_symbol_data(symbol)
        with s_data.lock:
            s_data.candles_m1.clear()
            s_data.current_candle = None
            
            if df.empty:
                return

            # Ensure sorted M1
            df_sorted = df.sort_index()
            
            # Convert to dict records
            records = df_sorted.reset_index().to_dict('records')
            
            # Populate deque
            for r in records:
                # Map DF columns to candle dict
                # Assuming index is timestamp name, or reset_index made it 'timestamp' or 'index'
                ts_key = 'timestamp' if 'timestamp' in r else 'index'
                
                candle = {
                    'timestamp': r.get(ts_key),
                    'open': r.get('open'),
                    'high': r.get('high'),
                    'low': r.get('low'),
                    'close': r.get('close'),
                    'volume': r.get('volume', 0)
                }
                s_data.candles_m1.append(candle)

market_data_manager = SharedMarketDataManager()
