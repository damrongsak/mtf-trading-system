import pandas as pd
import vectorbt as vbt
import numpy as np

def calculate_yang_zhang(open_s: pd.Series, high_s: pd.Series, low_s: pd.Series, close_s: pd.Series, window: int = 20) -> pd.Series:
    """
    Calculate Yang-Zhang Volatility (2000).
    Combines overnight volatility, open-to-close volatility, and Rogers-Satchell.
    """
    # 1. Component log-returns
    log_ho = np.log(high_s / open_s)
    log_lo = np.log(low_s / open_s)
    log_co = np.log(close_s / open_s)
    
    # Overnight returns (Open_t / Close_t-1)
    log_oc = np.log(open_s / close_s.shift(1))
    
    # 2. Rogers-Satchell Variance
    rs = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)
    rs_var = rs.rolling(window=window).mean()
    
    # 3. Open-to-Close Variance
    oc_var = log_co.rolling(window=window).var()
    
    # 4. Overnight Variance
    overnight_var = log_oc.rolling(window=window).var()
    
    # 5. Weighted average constant k
    k = 0.34 / (1.34 + (window + 1) / (window - 1))
    
    # 6. Combined Variance
    yz_var = overnight_var + k * oc_var + (1 - k) * rs_var
    
    # Return Annualized Std Dev (Assuming M15 data, or keep as raw for PIV?)
    # PIV usually expects raw standard deviation for the period, which is what we have here.
    return np.sqrt(yz_var)

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
    
def calculate_adr(high: pd.Series, low: pd.Series, window: int = 20) -> float:
    """
    Calculate Average Daily Range (ADR).
    This function expects high/low series of any timeframe, resamples to Daily within logic if needed,
    or assumes input is already Daily.
    
    For logic simplicity in vectorbt context, we often deal with Intraday data.
    To get ADR from Intraday data properly:
    1. Resample to Daily
    2. Calc (High - Low)
    3. Rolling Mean
    
    Returns the latest ADR value (scalar) or a Series aligned with input index? 
    For strategy use, we usually want the ADR of the *previous* completed day to apply to today.
    """
    # Check if index is datetime
    if not isinstance(high.index, pd.DatetimeIndex):
        raise ValueError("Index must be DatetimeIndex")
        
    # Resample to Daily to get Daily Ranges
    daily_high = high.resample('D').max()
    daily_low = low.resample('D').min()
    daily_range = daily_high - daily_low
    
    # Calculate SMA of Daily Range
    adr_series = daily_range.rolling(window=window).mean()
    
    # Realign with original index (ffill) so we have the 'prev day ADR' available at any intraday moment
    # We shift(1) because today's ADR is based on past 20 days EXCLUDING today (usually)
    # or including today? Standard ADR usually includes Closed days.
    # So we take adr_series, shift 1, and reindex.
    
    adr_shifted = adr_series.shift(1)
    
    # Reindex to original high index to broadcast values
    adr_aligned = adr_shifted.reindex(high.index, method='ffill')
    return adr_aligned

def detect_volatility_regime(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 20) -> pd.Series:
    """
    Detect volatility regime:
    - Low: ATR < SMA(ATR)
    - Expanding: ATR > SMA(ATR) AND ATR rising
    - Panic: ATR > 2 * SMA(ATR)
    """
    atr = calculate_atr(high, low, close, window=window)
    atr_sma = atr.rolling(window=window).mean()
    
    regime = pd.Series('Stable', index=close.index)
    
    low_mask = atr < atr_sma
    expanding_mask = (atr > atr_sma) & (atr > atr.shift(1))
    panic_mask = atr > (atr_sma * 2.0)
    
    regime.loc[low_mask] = 'Low'
    regime.loc[expanding_mask] = 'Expanding'
    regime.loc[panic_mask] = 'Panic'
    
    return regime
