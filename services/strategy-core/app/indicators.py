import pandas as pd
import vectorbt as vbt

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
