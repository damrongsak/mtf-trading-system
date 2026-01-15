import pandas as pd
import pandas_ta as ta

def calculate_ema(close: pd.Series, span: int) -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA).
    """
    return close.ewm(span=span, adjust=False).mean()

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
