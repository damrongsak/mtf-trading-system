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

def calculate_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """
    Calculate MACD (Moving Average Convergence Divergence).
    Returns a named tuple or object with .macd, .signal, .hist
    """
    return vbt.MACD.run(close, fast_window=fast, slow_window=slow, signal_window=signal)

def calculate_bbands(close: pd.Series, window: int = 20, alpha: int = 2):
    """
    Calculate Bollinger Bands.
    """
    return vbt.BBANDS.run(close, window=window, alpha=alpha)

def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14):
    """
    Calculate ADX using pandas-ta.
    Returns DataFrame with ADX, DMP, DMN columns.
    """
    df = pd.DataFrame({'high': high, 'low': low, 'close': close})
    # pandas-ta returns a DataFrame with columns ADX_14, DMP_14, DMN_14 by default
    adx_df = df.ta.adx(length=length)
    return adx_df

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
