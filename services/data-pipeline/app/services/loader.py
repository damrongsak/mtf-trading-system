import pandas as pd
from datetime import datetime
import pytz
from typing import List, Dict, Any

def load_candles_from_csv(file_path: str, symbol: str, timeframe: str) -> pd.DataFrame:
    """
    Load OHLCV data from a CSV file.
    Expected CSV columns: time, open, high, low, close, volume
    """
    try:
        df = pd.read_csv(file_path)
        
        # Normalize column names
        df.columns = [c.lower().strip() for c in df.columns]
        
        required_cols = ['time', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"CSV missing required columns: {required_cols}")
            
        # Parse timestamp
        df['timestamp'] = pd.to_datetime(df['time'])
        
        # Ensure timezone awareness (assume UTC if not present)
        if df['timestamp'].dt.tz is None:
            df['timestamp'] = df['timestamp'].dt.tz_localize(pytz.UTC)
        else:
            df['timestamp'] = df['timestamp'].dt.tz_convert(pytz.UTC)
            
        df['symbol'] = symbol
        df['timeframe'] = timeframe
        
        # Sort by time
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df[['symbol', 'timeframe', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
    except Exception as e:
        raise RuntimeError(f"Failed to load candles from {file_path}: {str(e)}")
