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
