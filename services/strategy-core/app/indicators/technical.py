import pandas as pd
# import pandas_ta as ta

def calculate_indicator(df: pd.DataFrame, strategy: str = "Common") -> pd.DataFrame:
    """
    Calculate indicators using native app.indicators.
    """
    if strategy == "Common":
        from app.indicators.trend import calculate_ema
        from app.indicators.momentum import calculate_rsi
        from app.indicators.volatility import calculate_atr
        
        df = df.copy()
        df['SMA_50'] = calculate_ema(df['close'], span=50) # SMA as EMA proxy
        df['RSI_14'] = calculate_rsi(df['close'], window=14)
        df['ATR_14'] = calculate_atr(df['high'], df['low'], df['close'], window=14)
    
    return df
