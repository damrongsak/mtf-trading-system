import pandas as pd
import vectorbt as vbt

def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR).
    """
    return vbt.ATR.run(high, low, close, window=window).atr

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
