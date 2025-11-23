import pandas as pd

def resample_candles(df: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
    """
    Resample 15m candles to a higher timeframe (1H, 4H, D).
    Expects a DataFrame with a DatetimeIndex or 'timestamp' column.
    """
    if df.empty:
        return pd.DataFrame()
        
    df = df.copy()
    if 'timestamp' in df.columns:
        df = df.set_index('timestamp')
        
    # Map timeframe string to pandas offset alias
    tf_map = {
        '1h': '1H',
        '4h': '4H',
        'd': '1D'
    }
    
    rule = tf_map.get(target_timeframe.lower())
    if not rule:
        raise ValueError(f"Unsupported target timeframe: {target_timeframe}")
        
    # Resampling logic
    # Open: first
    # High: max
    # Low: min
    # Close: last
    # Volume: sum
    
    resampled = df.resample(rule).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
        'symbol': 'first' # Keep symbol
    })
    
    # Drop incomplete candles (NaNs)
    resampled = resampled.dropna()
    
    # Reset index to make timestamp a column again
    resampled = resampled.reset_index()
    resampled['timeframe'] = target_timeframe
    
    return resampled
