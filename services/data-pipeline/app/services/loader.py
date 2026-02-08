import pandas as pd
import pytz
from typing import List, Dict, Any

class CsvValidationError(ValueError):
    """Custom exception for CSV validation errors."""
    pass

def load_candles_from_csv(file_path: str, symbol: str, timeframe: str) -> pd.DataFrame:
    """
    Load OHLCV data from a CSV file with robust validation.
    """
    try:
        # 1. File Format Check
        try:
            # Try reading with tab separator first (MetaTrader default)
            df = pd.read_csv(file_path, sep='\t')
            if len(df.columns) < 2:
                # Fallback to comma separator
                df = pd.read_csv(file_path, sep=',')
        except Exception:
            raise CsvValidationError("Invalid file format. Please upload a valid CSV.")

        # Normalize column names
        df.columns = [c.replace('<', '').replace('>', '').lower().strip() for c in df.columns]
        
        # Combine date and time for timestamp
        if 'date' in df.columns and 'time' in df.columns:
            df['time'] = df['date'].astype(str) + ' ' + df['time'].astype(str)
            df.drop(columns=['date'], inplace=True)

        # Rename columns to expected format
        rename_map = {'vol': 'volume', 'tickvol': 'volume', 'timestamp': 'time'}
        df.rename(columns=rename_map, inplace=True)
        
        # 2. Schema Validation
        required_cols = {'time', 'open', 'high', 'low', 'close', 'volume'}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            raise CsvValidationError(f"CSV missing required columns: {', '.join(missing_cols)}")
            
        # 3. Data Type Validation
        try:
            df['timestamp'] = pd.to_datetime(df['time'])
        except Exception:
             raise CsvValidationError("Column 'time' contains invalid timestamp formats.")
            
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            if df[col].isnull().any():
                 raise CsvValidationError(f"Column '{col}' contains non-numeric values.")

        # Ensure timezone awareness
        if df['timestamp'].dt.tz is None:
            df['timestamp'] = df['timestamp'].dt.tz_localize(pytz.UTC)
        else:
            df['timestamp'] = df['timestamp'].dt.tz_convert(pytz.UTC)

        # 4. Logical Validation
        if (df[['open', 'high', 'low', 'close']] < 0).any().any():
             raise CsvValidationError("Prices cannot be negative.")
        
        if (df['volume'] < 0).any():
            raise CsvValidationError("Volume cannot be negative.")

        if (df['high'] < df['low']).any():
            raise CsvValidationError("High must be >= Low")

        # 5. Final Formatting
        df['symbol'] = symbol
        df['timeframe'] = timeframe
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df[['symbol', 'timeframe', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
    except CsvValidationError as ve:
        raise ve
    except Exception as e:
        raise RuntimeError(f"Failed to process CSV: {str(e)}")
