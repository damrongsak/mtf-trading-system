import pandas as pd
import numpy as np

def detect_pin_bar(df: pd.DataFrame, body_ratio: float = 0.3, wick_ratio: float = 0.6) -> pd.Series:
    """
    Vectorized Pin Bar detection.
    A Pin Bar has a small body and a long wick on one side.
    
    Args:
        df: DataFrame with OHLC columns.
        body_ratio: Body must be less than this % of total range.
        wick_ratio: One wick must be greater than this % of total range.
        
    Returns:
        Series with 'bullish_pin', 'bearish_pin', or None.
    """
    high = df['high']
    low = df['low']
    open_ = df['open']
    close = df['close']
    
    total_range = high - low
    body = (close - open_).abs()
    
    # Avoid div by zero
    total_range_safe = total_range.replace(0, np.nan)
    
    # Ratios
    curr_body_ratio = body / total_range_safe
    
    upper_wick = high - df[['open', 'close']].max(axis=1)
    lower_wick = df[['open', 'close']].min(axis=1) - low
    
    upper_wick_ratio = upper_wick / total_range_safe
    lower_wick_ratio = lower_wick / total_range_safe
    
    # Conditions
    bullish_pin = (curr_body_ratio < body_ratio) & (lower_wick_ratio > wick_ratio)
    bearish_pin = (curr_body_ratio < body_ratio) & (upper_wick_ratio > wick_ratio)
    
    result = pd.Series(None, index=df.index, dtype=object)
    result.loc[bullish_pin] = 'BULLISH_PIN'
    result.loc[bearish_pin] = 'BEARISH_PIN'
    
    return result

def detect_inside_bar(df: pd.DataFrame) -> pd.Series:
    """
    Vectorized Inside Bar detection.
    Current High/Low is inside Previous High/Low.
    """
    high = df['high']
    low = df['low']
    
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    
    is_inside = (high < prev_high) & (low > prev_low)
    
    result = pd.Series(False, index=df.index)
    result.loc[is_inside] = True
    
    return result

def detect_engulfing(df: pd.DataFrame) -> pd.Series:
    """
    Vectorized Engulfing detection.
    """
    open_ = df['open']
    close = df['close']
    
    prev_open = open_.shift(1)
    prev_close = close.shift(1)
    
    bullish = (close > open_) & (prev_close < prev_open) & (close > prev_open) & (open_ < prev_close)
    bearish = (close < open_) & (prev_close > prev_open) & (close < prev_open) & (open_ > prev_close)
    
    result = pd.Series(None, index=df.index, dtype=object)
    result.loc[bullish] = 'BULLISH_ENGULFING'
    result.loc[bearish] = 'BEARISH_ENGULFING'
    
    return result
