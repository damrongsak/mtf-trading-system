
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

    def update_tick(self, symbol: str, price: float, timestamp: datetime, bid: Optional[float] = None, ask: Optional[float] = None):
        """
        Update the shared DataFrame for a symbol with a new tick.
        Synthesizes M15 candles and builds Footprint/Delta data.
        """
        with self.lock:
            df = self.data_buffers.get(symbol)
            if df is None:
                # Initialize with empty DF with proper columns
                # footprint: List of dicts (price ladder)
                # delta: Net buying volume
                df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'delta', 'footprint'])
                self.data_buffers[symbol] = df

            # Round timestamp to nearest 15m floor
            ts_floor = timestamp.replace(second=0, microsecond=0)
            minute = ts_floor.minute
            minute_floor = (minute // 15) * 15
            ts_floor = ts_floor.replace(minute=minute_floor)
            
            # Determine Aggressor Side (Tick Rule)
            # Default to Neutral/Unknown if no prior data
            # Side: 1 (Buy), -1 (Sell), 0 (Neutral)
            side = 0
            # We need the last price of the *stream*, not just the candle.
            # But here we only have the DF.
            # Ideally we check the last close of the last row.
            
            last_price = price
            if not df.empty:
                last_price = df.iloc[-1]['close'] # This is the close of the *candle*, which is the last tick.
            
            if price > last_price:
                side = 1
            elif price < last_price:
                side = -1
            else:
                # continuation (same as last tick? We don't track last tick side here explicitly, assume neutral or logic needed)
                # For MVP, treat flat as neutral or ignore for delta
                side = 0 

            # Volume for this tick
            # OANDA doesn't give true volume, so we use 1 tick = 1 vol unit (or liquidity if provided elsewhere)
            tick_vol = 1.0 
            
            # Build Footprint Entry Helper
            def update_footprint(fp_list, price_level, s, vol):
                if not isinstance(fp_list, list): fp_list = []
                # Find existing level
                found = False
                for level in fp_list:
                    if level['price'] == price_level:
                        if s == 1: level['ask_vol'] = level.get('ask_vol', 0) + vol
                        elif s == -1: level['bid_vol'] = level.get('bid_vol', 0) + vol
                        found = True
                        break
                if not found:
                    new_level = {'price': price_level, 'bid_vol': 0, 'ask_vol': 0}
                    if s == 1: new_level['ask_vol'] = vol
                    elif s == -1: new_level['bid_vol'] = vol
                    fp_list.append(new_level)
                return fp_list

            if df.empty:
                # First Candle
                new_row = {
                    'timestamp': ts_floor,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': tick_vol,
                    'delta': tick_vol if side == 1 else (-tick_vol if side == -1 else 0),
                    'footprint': update_footprint([], price, side, tick_vol)
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
                    'volume': tick_vol,
                    'delta': tick_vol if side == 1 else (-tick_vol if side == -1 else 0),
                    'footprint': update_footprint([], price, side, tick_vol)
                }
                self.data_buffers[symbol] = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                
            elif ts_floor == last_ts:
                # Update existing candle
                curr_high = df.at[last_row_idx, 'high']
                curr_low = df.at[last_row_idx, 'low']
                curr_delta = df.at[last_row_idx, 'delta']
                if pd.isna(curr_delta): curr_delta = 0
                
                # Update OHLC
                df.at[last_row_idx, 'high'] = max(curr_high, price)
                df.at[last_row_idx, 'low'] = min(curr_low, price)
                df.at[last_row_idx, 'close'] = price
                df.at[last_row_idx, 'volume'] += tick_vol
                
                # Update Delta
                if side == 1:
                    df.at[last_row_idx, 'delta'] = curr_delta + tick_vol
                elif side == -1:
                    df.at[last_row_idx, 'delta'] = curr_delta - tick_vol
                    
                # Update Footprint
                # Need to be careful with pandas cell update for mutable objects (list/dict)
                # It's safer to read, modify, write back
                curr_fp = df.at[last_row_idx, 'footprint']
                updated_fp = update_footprint(curr_fp, price, side, tick_vol)
                df.at[last_row_idx, 'footprint'] = updated_fp

    def get_data(self, symbol: str) -> pd.DataFrame:
        with self.lock:
            return self.data_buffers.get(symbol, pd.DataFrame()).copy()

    def set_data(self, symbol: str, df: pd.DataFrame):
        with self.lock:
            self.data_buffers[symbol] = df

market_data_manager = SharedMarketDataManager()
