
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

    def update_quote(self, symbol: str, tick: dict):
        """
        Update the shared DataFrame for a symbol with a new tick/candle.
        This is a simplified implementation. Real implementation handles OHLCV aggregation.
        """
        with self.lock:
            if symbol not in self.data_buffers:
                # Initialize with empty or fetch initial
                self.data_buffers[symbol] = pd.DataFrame()
            
            # Logic to append tick/update current candle would go here
            # For now, assuming we are receiving closed candles or managing a small buffer
            pass

    def get_data(self, symbol: str) -> pd.DataFrame:
        with self.lock:
            return self.data_buffers.get(symbol, pd.DataFrame()).copy()

    def set_data(self, symbol: str, df: pd.DataFrame):
        with self.lock:
            self.data_buffers[symbol] = df

market_data_manager = SharedMarketDataManager()
