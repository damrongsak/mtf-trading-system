import pandas as pd
import logging

logger = logging.getLogger(__name__)

def resample_candles(df: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
    """
    Resample candles to a higher timeframe (1H, 4H, D).
    
    Args:
        df: DataFrame with 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol'
        target_timeframe: target timeframe string (e.g., '1h', '4h', 'd')
        
    Returns:
        Resampled DataFrame
    """
    if df.empty:
        return pd.DataFrame()
        
    df = df.copy()
    
    # Ensure datetime index
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
        
    # Map timeframe string to pandas offset alias
    tf_map = {
        '1h': '1H',
        '4h': '4H',
        'd': '1D',
        '1d': '1D'
    }
    
    rule = tf_map.get(target_timeframe.lower())
    if not rule:
        available = ", ".join(tf_map.keys())
        raise ValueError(f"Unsupported target timeframe: {target_timeframe}. Available: {available}")
        
    # Resampling aggregation rules
    agg_rules = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }
    
    # If symbol exists, keep it
    if 'symbol' in df.columns:
        agg_rules['symbol'] = 'first'
    
    try:
        resampled = df.resample(rule).agg(agg_rules)
        
        # Drop incomplete candles (NaNs)
        resampled = resampled.dropna(subset=['open', 'close'])
        
        # Reset index and restore metadata
        resampled = resampled.reset_index()
        resampled['timeframe'] = target_timeframe
        
        return resampled
        
    except Exception as e:
        logger.error(f"Resampling failed: {e}")
        raise RuntimeError(f"Resampling error: {str(e)}")
