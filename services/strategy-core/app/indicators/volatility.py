import pandas as pd
import vectorbt as vbt
import numpy as np
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.schemas import DetailedIndicatorResponse, IndicatorMetadata, IndicatorInterpretation
from app.utils.interpretation import get_atr_interpretation

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
    
    # Return Standard Deviation
    return np.sqrt(yz_var)

def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """Calculate Average True Range (ATR) using vectorbt."""
    return vbt.ATR.run(high, low, close, window=window).atr

def calculate_atr_detailed(
    high: pd.Series, 
    low: pd.Series, 
    close: pd.Series, 
    symbol: str,
    timeframe: str,
    window: int = 14,
    fund_id: Optional[str] = None,
    data_source: str = "CTRADER"
) -> DetailedIndicatorResponse:
    """Institutional-grade ATR calculation with white-box metadata."""
    start_time = time.time()
    
    atr_series = calculate_atr(high, low, close, window=window)
    
    # Standard cleaning for JSON
    values = [float(v) if not pd.isna(v) else None for v in atr_series.values]
    
    # Interpretation for the latest value
    latest_atr = atr_series.iloc[-1] if not atr_series.empty else 0.0
    latest_close = close.iloc[-1] if not close.empty else 1.0
    interpretation = get_atr_interpretation(latest_atr, latest_close)
    
    latency = (time.time() - start_time) * 1000
    
    meta = IndicatorMetadata(
        parameters={"window": window},
        formula="ATR = SMA(True Range, window)",
        data_source=data_source,
        resolved_symbol=symbol,
        calc_latency_ms=latency,
        fund_context=fund_id,
        timeframe=timeframe
    )
    
    return DetailedIndicatorResponse(
        values=values,
        meta=meta,
        interpretation=interpretation
    )

def calculate_bbands(close: pd.Series, window: int = 20, alpha: int = 2) -> pd.DataFrame:
    """
    Calculate Bollinger Bands using vectorbt.
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
    
def calculate_adr(high: pd.Series, low: pd.Series, window: int = 20) -> pd.Series:
    """Calculate Average Daily Range (ADR)."""
    if not isinstance(high.index, pd.DatetimeIndex):
        # If not datetime, assume already daily or cannot calc adr correctly
        daily_range = high - low
        return daily_range.rolling(window=window).mean()
        
    daily_high = high.resample('D').max()
    daily_low = low.resample('D').min()
    daily_range = daily_high - daily_low
    adr_series = daily_range.rolling(window=window).mean()
    
    adr_shifted = adr_series.shift(1)
    adr_aligned = adr_shifted.reindex(high.index, method='ffill')
    return adr_aligned

def detect_volatility_regime(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 20) -> pd.Series:
    """Detect volatility regime using institutional logic."""
    atr = calculate_atr(high, low, close, window=window)
    atr_sma = atr.rolling(window=window).mean()
    
    regime = pd.Series('Stable', index=close.index)
    
    low_mask = atr < (atr_sma * 0.8)
    expanding_mask = (atr > atr_sma) & (atr > atr.shift(1))
    panic_mask = atr > (atr_sma * 1.5)
    
    regime.loc[low_mask] = 'Low'
    regime.loc[expanding_mask] = 'Expanding'
    regime.loc[panic_mask] = 'Panic'
    
    return regime
