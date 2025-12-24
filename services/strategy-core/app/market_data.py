
import pandas as pd
from typing import Dict, Optional, List
from datetime import datetime
import threading

class SharedMarketDataManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SharedMarketDataManager, cls).__new__(cls)
                cls._instance.data_buffers = {} # Dict[symbol, pd.DataFrame]
                cls._instance.lock = threading.RLock()
        return cls._instance

    def update_tick(self, symbol: str, price: float, timestamp: datetime):
        """
        Update the shared DataFrame for a symbol with a new tick.
        Synthesizes M15 candles by default.
        """
        with self.lock:
            df = self.data_buffers.get(symbol)
            if df is None:
                # Initialize with empty DF with proper columns
                df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                self.data_buffers[symbol] = df

            # Round timestamp to nearest 15m floor
            # Simple floor logic
            ts_floor = timestamp.replace(second=0, microsecond=0)
            minute = ts_floor.minute
            minute_floor = (minute // 15) * 15
            ts_floor = ts_floor.replace(minute=minute_floor)
            
            # Check if DF is empty
            if df.empty:
                new_row = {
                    'timestamp': ts_floor,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': 1
                }
                self.data_buffers[symbol] = pd.DataFrame([new_row])
                return

            last_row_idx = df.index[-1]
            last_ts = df.at[last_row_idx, 'timestamp']
            
            if ts_floor > last_ts:
                # New Candle
                new_row = {
                    'timestamp': ts_floor,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': 1
                }
                # Use concat for new row to return new DF? Or append?
                # Optimisation: List buffer then concat is better, but for single row append:
                # concat is slow. simpler to append to list if we maintained list.
                # For this MVP, concat is "safe" but slow. 
                # Improving: self.data_buffers[symbol] = pd.concat(...)
                self.data_buffers[symbol] = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                
            elif ts_floor == last_ts:
                # Update existing candle
                curr_high = df.at[last_row_idx, 'high']
                curr_low = df.at[last_row_idx, 'low']
                
                df.at[last_row_idx, 'high'] = max(curr_high, price)
                df.at[last_row_idx, 'low'] = min(curr_low, price)
                df.at[last_row_idx, 'close'] = price
                df.at[last_row_idx, 'volume'] += 1 # Tick volume
                
            # If tick is older (latency), ignore or update past? Ignore for now.

    def get_data(self, symbol: str) -> pd.DataFrame:
        with self.lock:
            return self.data_buffers.get(symbol, pd.DataFrame()).copy()

    def set_data(self, symbol: str, df: pd.DataFrame):
        with self.lock:
            self.data_buffers[symbol] = df

market_data_manager = SharedMarketDataManager()
