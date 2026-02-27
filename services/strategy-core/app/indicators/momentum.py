import pandas as pd
# import vectorbt as vbt

def calculate_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).
    """
    import vectorbt as vbt
    return vbt.RSI.run(close, window=window).rsi

def calculate_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    Returns DataFrame with columns: macd, signal, hist
    """
    import vectorbt as vbt
    res = vbt.MACD.run(close, fast_window=fast, slow_window=slow, signal_window=signal)
    df = pd.DataFrame({
        'macd': res.macd,
        'signal': res.signal,
        'hist': res.hist
    })
    return df
