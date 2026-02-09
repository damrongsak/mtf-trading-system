import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from numba import njit
import vectorbt as vbt

@njit(cache=False)
def volume_profile_nb(close, volume, bins):
    """
    Calculate Volume Profile using Numba.
    
    Args:
        close (float[:]): Close price array
        volume (float[:]): Volume array
        bins (int): Number of bins
        
    Returns:
        (float[:], float[:]): Tuple of (price_levels, volumes)
    """
    price_min = np.min(close)
    price_max = np.max(close)
    
    # Avoid division by zero
    if price_max == price_min:
        return np.array([price_min]), np.array([np.sum(volume)])
        
    price_range = price_max - price_min
    bin_size = price_range / bins
    
    # Initialize output arrays
    # We use bins + 1 size potentially to handle edge cases, but standard is bins
    # Let's stick to strict bins.
    
    bucket_vols = np.zeros(bins)
    
    n = len(close)
    for i in range(n):
        # Determine bucket index
        # formula: floor((price - min) / bin_size)
        idx = int((close[i] - price_min) / bin_size)
        
        # Clip to max bin index (handle max price case which equals bins)
        if idx >= bins:
            idx = bins - 1
        if idx < 0: 
            idx = 0
            
        bucket_vols[idx] += volume[i]
        
    # Calculate price levels (center of bins or start?)
    # Previous implementation was: price_min + (bucket * bin_size) -> Start of bin
    price_levels = np.empty(bins)
    for i in range(bins):
        price_levels[i] = price_min + (i * bin_size)
        
    return price_levels, bucket_vols

def calculate_vwap(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Calculate Cumulative Volume Weighted Average Price (VWAP).
    """
    v_c = volume * close
    return v_c.cumsum() / volume.cumsum()

def detect_liquidity_condition(volume: pd.Series, close: pd.Series, window: int = 20) -> Dict[str, Any]:
    """
    Identify liquidity conditions based on Relative Volume (RVOL) and Volume Profile.
    """
    avg_vol = volume.rolling(window=window).mean()
    rvol = volume / avg_vol
    
    current_rvol = rvol.iloc[-1]
    
    # Classify Liquidity
    if current_rvol > 2.0:
        condition = "High (Institutional Hub)"
    elif current_rvol > 1.2:
        condition = "Expanding"
    elif current_rvol < 0.8:
        condition = "Low (Thin Market)"
    else:
        condition = "Neutral"
        
    return {
        "rvol": round(float(current_rvol), 2),
        "condition": condition,
        "is_high_volume_node": bool(current_rvol > 1.5) # Simple proxy for now
    }

def calculate_volume_profile(df: pd.DataFrame, bins: int = 10) -> pd.DataFrame:
    """
    Calculate Volume Profile (Price-by-Volume) using Numba acceleration.
    """
    close_arr = df['close'].values
    vol_arr = df['volume'].values.astype(np.float64) 
    
    levels, vols = volume_profile_nb(close_arr, vol_arr, bins)
    
    return pd.DataFrame({
        'price_level': levels,
        'volume': vols
    })
