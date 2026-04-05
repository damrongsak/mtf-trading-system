import pandas as pd
import numpy as np
import vectorbt as vbt
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.schemas import DetailedIndicatorResponse, IndicatorMetadata, IndicatorInterpretation

logger = logging.getLogger(__name__)

def calculate_ema(close: pd.Series, span: int) -> pd.Series:
    """Calculate Exponential Moving Average (EMA) using vectorbt."""
    # VectorBT MA with as_ema=True
    return vbt.MA.run(close, window=span, ewm=True).ma

def calculate_ema_detailed(
    close: pd.Series,
    symbol: str,
    timeframe: str,
    span: int = 20,
    fund_id: Optional[str] = None,
    data_source: str = "CTRADER"
) -> DetailedIndicatorResponse:
    """Institutional-grade EMA calculation with white-box metadata."""
    start_time = time.time()
    ema_series = calculate_ema(close, span=span)
    
    values = [float(v) if not pd.isna(v) else None for v in ema_series.values]
    
    # Interpretation: Price relative to EMA
    latest_ema = ema_series.iloc[-1] if not ema_series.empty else 0.0
    latest_price = close.iloc[-1] if not close.empty else 0.0
    
    bias = "NEUTRAL"
    strength = 0.5
    summary = f"Price is consolidated around EMA({span})."
    advice = f"Wait for a clear breakout from EMA({span}) for trend confirmation."
    
    pct_diff = ((latest_price - latest_ema) / latest_ema * 100) if latest_ema != 0 else 0
    
    if latest_price > latest_ema:
        bias = "BULLISH"
        strength = min(0.5 + (pct_diff / 5.0), 1.0) # 5% diff = 1.0 strength
        summary = f"Price is above EMA({span}) (Bullish Trend)."
        advice = f"Maintain bullish bias as long as price holds above EMA({span})."
    elif latest_price < latest_ema:
        bias = "BEARISH"
        strength = min(0.5 + (abs(pct_diff) / 5.0), 1.0)
        summary = f"Price is below EMA({span}) (Bearish Trend)."
        advice = f"Maintain bearish bias as long as price stays below EMA({span})."
        
    interpretation = IndicatorInterpretation(
        summary=summary,
        bias=bias,
        strength=strength,
        ai_advice=advice
    )
    
    latency = (time.time() - start_time) * 1000
    
    meta = IndicatorMetadata(
        parameters={"span": span},
        formula=f"EMA(t) = Price(t) * k + EMA(t-1) * (1-k); k = 2/(span+1)",
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

def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.DataFrame:
    """
    Optimized ADX calculation using VectorBT primitives.
    """
    # VectorBT doesn't have a direct 'ADX' run yet in all versions, 
    # but we can use their indicators or stick to our optimized Wilder's smoothing logic.
    # Actually, vbt.ADX exists in newer versions.
    try:
        res = vbt.ADX.run(high, low, close, window=length)
        return pd.DataFrame({
            'adx': res.adx,
            'dmp': res.plus_di,
            'dmn': res.minus_di
        }, index=close.index)
    except Exception:
        # Fallback to manual optimized Wilder's
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        plus_dm = pd.Series(0.0, index=close.index)
        plus_dm.loc[(up_move > down_move) & (up_move > 0)] = up_move
        
        minus_dm = pd.Series(0.0, index=close.index)
        minus_dm.loc[(down_move > up_move) & (down_move > 0)] = down_move
        
        alpha = 1.0 / length
        atr = tr.ewm(alpha=alpha, adjust=False, min_periods=length).mean()
        plus_di_smooth = plus_dm.ewm(alpha=alpha, adjust=False, min_periods=length).mean()
        minus_di_smooth = minus_dm.ewm(alpha=alpha, adjust=False, min_periods=length).mean()
        
        plus_di = 100 * (plus_di_smooth / atr)
        minus_di = 100 * (minus_di_smooth / atr)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        adx = dx.ewm(alpha=alpha, adjust=False, min_periods=length).mean()
        
        return pd.DataFrame({
            'adx': adx,
            'dmp': plus_di,
            'dmn': minus_di
        }, index=close.index).replace([np.inf, -np.inf], np.nan)

def detect_trend_structure(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.DataFrame:
    """Detect trend structure and compression (Squeeze) using optimized indicators."""
    adx_df = calculate_adx(high, low, close, length=length)
    
    res_bb = vbt.BBANDS.run(close, window=20, alpha=2)
    bb_width = res_bb.upper - res_bb.lower
    
    kc_mid = calculate_ema(close, span=20)
    atr_20 = vbt.ATR.run(high, low, close, window=20).atr
    kc_width = (2.0 * atr_20) * 2 # Upper - Lower = 4 * ATR usually in KC
    
    structure = pd.Series('Neutral', index=close.index)
    adx_values = adx_df['adx']
    valid_adx = adx_values.notna()
    
    structure.loc[valid_adx & (adx_values > 25)] = 'Trending'
    structure.loc[valid_adx & (adx_values < 20)] = 'Range'
    
    is_squeeze = bb_width < kc_width
    
    return pd.DataFrame({
        'structure': structure,
        'is_squeeze': is_squeeze,
        'adx': adx_values
    }, index=close.index)
