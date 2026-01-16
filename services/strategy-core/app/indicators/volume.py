import pandas as pd
import numpy as np
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

def calculate_volume_profile(close: pd.Series, volume: pd.Series, bins: int = 24) -> pd.DataFrame:
    """
    Calculate Volume Profile (Price-by-Volume) using Numba acceleration.
    Returns a DataFrame with price levels and volume at that level.
    """
    # Ensure numpy arrays (copy=False for speed if possible)
    close_arr = close.values
    
    # Handle volume if integer or float
    # Numba likes homogeneous types. If volume is int and close is float, strict typing might complain 
    # if we don't handle it. But standard python types usually work with JIT.
    # Safe cast to float for volume to match expected bucket_vols type
    vol_arr = volume.values.astype(np.float64) 
    
    levels, vols = volume_profile_nb(close_arr, vol_arr, bins)
    
    return pd.DataFrame({
        'price_level': levels,
        'volume': vols
    })
