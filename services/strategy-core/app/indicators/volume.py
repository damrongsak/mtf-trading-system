import pandas as pd

def calculate_volume_profile(close: pd.Series, volume: pd.Series, bins: int = 24) -> pd.DataFrame:
    """
    Calculate Volume Profile (Price-by-Volume).
    Returns a DataFrame with price levels and volume at that level.
    """
    # 1. Create Price Buckets
    price_min = close.min()
    price_max = close.max()
    price_range = price_max - price_min
    bin_size = price_range / bins
    
    # 2. Assign each bar's volume to a price bucket
    # Simplified logic: Uses Close price to determine bucket. 
    # More advanced: Distribute volume across High-Low.
    df = pd.DataFrame({'close': close, 'volume': volume})
    df['bucket'] = ((df['close'] - price_min) / bin_size).astype(int)
    
    # Clip buckets to be within [0, bins-1]
    df['bucket'] = df['bucket'].clip(lower=0, upper=bins-1)
    
    # 3. Sum volume per bucket
    vp = df.groupby('bucket')['volume'].sum().reset_index()
    
    # 4. Calculate Price Level for each bucket
    vp['price_level'] = price_min + (vp['bucket'] * bin_size)
    
    return vp[['price_level', 'volume']]
