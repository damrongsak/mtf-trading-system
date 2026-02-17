import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

def calculate_pivots(df: pd.DataFrame, timeframe: str = 'D', method: str = 'traditional') -> pd.DataFrame:
    """
    Calculate Pivot Points and broadcast them back to the original index.
    Supports: traditional, camarilla, woodie.
    """
    if df.empty:
        return pd.DataFrame()

    # 1. Resample to get the H, L, C of the specified timeframe
    # We use closed days, so we need the previous period's data.
    resampled = df.resample(timeframe).agg({
        'high': 'max',
        'low': 'min',
        'close': 'last'
    })
    
    # 2. Shift by 1 so that 'today' knows 'yesterday's' pivots
    prev_high = resampled['high'].shift(1)
    prev_low = resampled['low'].shift(1)
    prev_close = resampled['close'].shift(1)
    
    p = pd.Series(dtype=float, index=resampled.index)
    r1, r2, r3, r4 = [pd.Series(dtype=float, index=resampled.index) for _ in range(4)]
    s1, s2, s3, s4 = [pd.Series(dtype=float, index=resampled.index) for _ in range(4)]
    
    h_l = prev_high - prev_low
    
    if method == 'traditional':
        p = (prev_high + prev_low + prev_close) / 3
        r1 = 2 * p - prev_low
        s1 = 2 * p - prev_high
        r2 = p + h_l
        s2 = p - h_l
        r3 = prev_high + 2 * (p - prev_low)
        s3 = prev_low - 2 * (prev_high - p)
    
    elif method == 'camarilla':
        p = prev_close # Camarilla uses close as base
        r1 = prev_close + h_l * (1.1 / 12)
        s1 = prev_close - h_l * (1.1 / 12)
        r2 = prev_close + h_l * (1.1 / 6)
        s2 = prev_close - h_l * (1.1 / 6)
        r3 = prev_close + h_l * (1.1 / 4)
        s3 = prev_close - h_l * (1.1 / 4)
        r4 = prev_close + h_l * (1.1 / 2)
        s4 = prev_close - h_l * (1.1 / 2)
        
    elif method == 'woodie':
        p = (prev_high + prev_low + 2 * prev_close) / 4
        r1 = 2 * p - prev_low
        s1 = 2 * p - prev_high
        r2 = p + h_l
        s2 = p - h_l
        r3 = prev_high + 2 * (p - prev_low) # Woodie R3/S3 often same as traditional
        s3 = prev_low - 2 * (prev_high - p)

    # Combine into a DataFrame
    pivots_resampled = pd.DataFrame({
        f'pivot_{timeframe}_{method}': p,
        f'r1_{timeframe}_{method}': r1,
        f's1_{timeframe}_{method}': s1,
        f'r2_{timeframe}_{method}': r2,
        f's2_{timeframe}_{method}': s2,
        f'r3_{timeframe}_{method}': r3,
        f's3_{timeframe}_{method}': s3,
    })
    
    if method == 'camarilla':
        pivots_resampled[f'r4_{timeframe}_{method}'] = r4
        pivots_resampled[f's4_{timeframe}_{method}'] = s4

    # 3. Broadcast back to original index using ffill
    # Note: reindex + ffill is safe because of the shift(1)
    pivots_aligned = pivots_resampled.reindex(df.index, method='ffill')
    
    return pivots_aligned

def calculate_all_pivots(df: pd.DataFrame, timeframes=None, method='traditional') -> pd.DataFrame:
    """
    Calculate pivots for multiple timeframes and merge them.
    Defaults: H1, H4, D, W, M.
    """
    if timeframes is None:
        timeframes = ['1h', '4h', 'D', 'W', 'M']
    
    # We need to normalize timeframes to pandas frequency strings
    # H1 -> 1h, H4 -> 4h, Daily -> D, Weekly -> W, Monthly -> M
    mapping = {
        'H1': '1h',
        'H4': '4h',
        'Daily': 'D',
        'Weekly': 'W',
        'Monthly': 'ME' # 'M' is deprecated for 'ME' in newer pandas
    }
    
    results = []
    for tf in timeframes:
        freq = mapping.get(tf, tf)
        piv_tf = calculate_pivots(df, timeframe=freq, method=method)
        results.append(piv_tf)
        
    return pd.concat(results, axis=1)
