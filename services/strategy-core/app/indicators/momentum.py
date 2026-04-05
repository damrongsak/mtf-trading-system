import pandas as pd
import vectorbt as vbt
import numpy as np
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.schemas import DetailedIndicatorResponse, IndicatorMetadata, IndicatorInterpretation
from app.utils.interpretation import get_rsi_interpretation, get_macd_interpretation

def calculate_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI) using vectorbt."""
    return vbt.RSI.run(close, window=window).rsi

def calculate_rsi_detailed(
    close: pd.Series,
    symbol: str,
    timeframe: str,
    window: int = 14,
    fund_id: Optional[str] = None,
    data_source: str = "CTRADER"
) -> DetailedIndicatorResponse:
    """Institutional-grade RSI calculation with white-box metadata."""
    start_time = time.time()
    rsi_series = calculate_rsi(close, window=window)
    
    values = [float(v) if not pd.isna(v) else None for v in rsi_series.values]
    
    latest_rsi = rsi_series.iloc[-1] if not rsi_series.empty else 50.0
    interpretation = get_rsi_interpretation(latest_rsi, window)
    
    latency = (time.time() - start_time) * 1000
    
    meta = IndicatorMetadata(
        parameters={"window": window},
        formula="RSI = 100 - (100 / (1 + RS)) where RS = SmoothAvgGain / SmoothAvgLoss",
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

def calculate_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Calculate MACD (Moving Average Convergence Divergence) using vectorbt.
    Returns DataFrame with columns: macd, signal, hist
    """
    res = vbt.MACD.run(close, fast_window=fast, slow_window=slow, signal_window=signal)
    df = pd.DataFrame({
        'macd': res.macd,
        'signal': res.signal,
        'hist': res.hist
    })
    return df

def calculate_macd_detailed(
    close: pd.Series,
    symbol: str,
    timeframe: str,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    fund_id: Optional[str] = None,
    data_source: str = "CTRADER"
) -> DetailedIndicatorResponse:
    """Institutional-grade MACD calculation with white-box metadata."""
    start_time = time.time()
    macd_df = calculate_macd(close, fast, slow, signal)
    
    # For DetailedIndicatorResponse, we return the 'macd' line in 'values' 
    # but we could also return a more complex structure if we wanted.
    # However, standard schema has 'values: List[Optional[float]]'. 
    # For MACD, 'values' will be the MACD line. Others in meta/interpretation?
    # Actually, IndicatorResponse was simpler. DetailedIndicatorResponse should probably stick to one primary line
    # or we might need a multi-line schema later. For now, values = macd.
    
    values = [float(v) if not pd.isna(v) else None for v in macd_df['macd'].values]
    
    latest_macd = macd_df['macd'].iloc[-1] if not macd_df.empty else 0.0
    latest_sig = macd_df['signal'].iloc[-1] if not macd_df.empty else 0.0
    latest_hist = macd_df['hist'].iloc[-1] if not macd_df.empty else 0.0
    
    interpretation = get_macd_interpretation(latest_macd, latest_sig, latest_hist)
    
    latency = (time.time() - start_time) * 1000
    
    meta = IndicatorMetadata(
        parameters={"fast": fast, "slow": slow, "signal": signal},
        formula="MACD = EMA(fast) - EMA(slow); Signal = EMA(MACD, signal)",
        data_source=data_source,
        resolved_symbol=symbol,
        calc_latency_ms=latency,
        fund_context=fund_id,
        timeframe=timeframe
    )
    
    # Add extra lines to interpretation for now
    interpretation.summary += f" | Hist: {round(latest_hist, 4)}"
    
    return DetailedIndicatorResponse(
        values=values,
        meta=meta,
        interpretation=interpretation
    )
