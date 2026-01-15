import pandas as pd
import vectorbt as vbt
import pandas_ta as ta

def calculate_ema(close: pd.Series, span: int) -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA).
    """
    return close.ewm(span=span, adjust=False).mean()

def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR).
    """
    return vbt.ATR.run(high, low, close, window=window).atr

def calculate_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).
    """
    return vbt.RSI.run(close, window=window).rsi

def calculate_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    Returns DataFrame with columns: macd, signal, hist
    """
    res = vbt.MACD.run(close, fast_window=fast, slow_window=slow, signal_window=signal)
    df = pd.DataFrame({
        'macd': res.macd,
        'signal': res.signal,
        'hist': res.hist
    })
    return df

def calculate_bbands(close: pd.Series, window: int = 20, alpha: int = 2) -> pd.DataFrame:
    """
    Calculate Bollinger Bands.
    Returns DataFrame with columns: middle, upper, lower, bandwidth, percent_b
    """
    res = vbt.BBANDS.run(close, window=window, alpha=alpha)
    df = pd.DataFrame({
        'middle': res.middle,
        'upper': res.upper,
        'lower': res.lower,
        'bandwidth': res.bandwidth,
        'percent_b': res.percent_b
    })
    return df

def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.DataFrame:
    """
    Calculate ADX using pandas-ta.
    Returns DataFrame with columns: adx, dmp, dmn
    """
    df = pd.DataFrame({'high': high, 'low': low, 'close': close})
    # pandas-ta returns a DataFrame with columns ADX_14, DMP_14, DMN_14 by default (depending on version)
    adx_df = df.ta.adx(length=length)
    
    # Normalize column names
    if adx_df is not None and not adx_df.empty:
        # Expected cols: ADX_14, DMP_14, DMN_14. We want generic adx, dmp, dmn
        # We can map by index or partial name match.
        # usually: [ADX_len, DMP_len, DMN_len]
        cols = adx_df.columns
        rename_map = {}
        for c in cols:
            if c.startswith('ADX'): rename_map[c] = 'adx'
            elif c.startswith('DMP'): rename_map[c] = 'dmp'
            elif c.startswith('DMN'): rename_map[c] = 'dmn'
        
        adx_df = adx_df.rename(columns=rename_map)
        
    return adx_df[['adx', 'dmp', 'dmn']] if adx_df is not None else pd.DataFrame(columns=['adx', 'dmp', 'dmn'])


def calculate_indicator(df: pd.DataFrame, strategy: str = "Common") -> pd.DataFrame:
    """
    Calculate indicators using pandas-ta.
    supports executing a 'Strategy' (pandas_ta concept) or specific indicators.
    """
    if strategy == "All":
        df.ta.strategy("All")
    elif strategy == "Common":
        # Example common strategy using direct calls
        df.ta.sma(length=50, append=True)
        df.ta.sma(length=200, append=True)
        df.ta.rsi(append=True)
        df.ta.atr(length=14, append=True)
    
    return df


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
