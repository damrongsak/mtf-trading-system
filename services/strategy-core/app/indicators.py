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

