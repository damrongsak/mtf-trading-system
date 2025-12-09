import pandas as pd
from datetime import datetime
import pytz
from typing import List, Dict, Any
import numpy as np

def load_candles_from_csv(file_path: str, symbol: str, timeframe: str) -> pd.DataFrame:
    """
    Load OHLCV data from a CSV file with robust validation.
    Expected CSV columns: time, open, high, low, close, volume
    Handles specific column names found in Dukascopy/MetaTrader exports like <DATE>, <TIME>, <OPEN>, etc.
    """
    try:
        # 1. File Format Check (Implicit in read_csv)
        try:
            df = pd.read_csv(file_path, sep='\t') # Use tab as separator for common MetaTrader CSVs
        except Exception:
            raise ValueError("Invalid file format. Please upload a valid CSV.")

        # Normalize column names
        df.columns = [c.replace('<', '').replace('>', '').lower().strip() for c in df.columns]
        
        # Combine date and time for timestamp
        if 'date' in df.columns and 'time' in df.columns:
            df['time'] = df['date'] + ' ' + df['time']
            df.drop(columns=['date'], inplace=True)

        # Rename columns to expected format if they exist
        df.rename(columns={'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'vol': 'volume'}, inplace=True)

        # 2. Schema Validation
        required_cols = {'time', 'open', 'high', 'low', 'close', 'volume'}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            raise ValueError(f"CSV missing required columns: {', '.join(missing_cols)}")
            
        # 3. Data Type Validation
        try:
            df['timestamp'] = pd.to_datetime(df['time'])
        except Exception:
            raise ValueError("Column 'time' contains invalid timestamp formats.")
            
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            if df[col].isnull().any():
                raise ValueError(f"Column '{col}' contains non-numeric values.")

        # Ensure timezone awareness (assume UTC if not present)
        if df['timestamp'].dt.tz is None:
            df['timestamp'] = df['timestamp'].dt.tz_localize(pytz.UTC)
        else:
            df['timestamp'] = df['timestamp'].dt.tz_convert(pytz.UTC)

        # 4. Range Checks & Logical Validation
        # Prices >= 0
        if (df[['open', 'high', 'low', 'close']] < 0).any().any():
             raise ValueError("Prices cannot be negative.")
        
        # Volume >= 0
        if (df['volume'] < 0).any():
            raise ValueError("Volume cannot be negative.")

        # High >= Low
        if (df['high'] < df['low']).any():
            invalid_rows = df[df['high'] < df['low']].index.tolist()
            raise ValueError(f"High must be >= Low (Check rows: {invalid_rows[:5]})")

        # High >= Open/Close
        if (df['high'] < df[['open', 'close']].max(axis=1)).any():
             raise ValueError("High must be greater than or equal to Open and Close.")

        # Low <= Open/Close
        if (df['low'] > df[['open', 'close']].min(axis=1)).any():
             raise ValueError("Low must be less than or equal to Open and Close.")
            
        df['symbol'] = symbol
        df['timeframe'] = timeframe
        
        # Sort by time
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df[['symbol', 'timeframe', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
    except ValueError as ve:
        raise ve
    except Exception as e:
        raise RuntimeError(f"Failed to process CSV: {str(e)}")
