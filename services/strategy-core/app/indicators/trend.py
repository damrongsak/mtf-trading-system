import pandas as pd
import numpy as np
import vectorbt as vbt
import logging

logger = logging.getLogger(__name__)

def calculate_ema(close: pd.Series, span: int) -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA).
    """
    return close.ewm(span=span, adjust=False).mean()

def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.DataFrame:
    """
    Optimized ADX calculation using VectorBT's native implementation.
    Includes warm-up period validation to prevent '0.0' or 'NaN' anomalies.
    """
    # 1. Check for sufficient data (Wilder's Smoothing needs significant warm-up)
    # Welles Wilder recommended at least 2 * length + a safety margin for stability.
    min_required = length * 2
    actual_length = len(close)
    
    if actual_length < min_required:
        logger.warning(f"ADX Calculation: Insufficient data points ({actual_length}). "
                       f"Required at least {min_required} for stable ADX. "
                       f"Returning NaN results.")
        # Return NaN DataFrame with correct index to maintain consistency
        return pd.DataFrame({
            'adx': [np.nan] * actual_length,
            'dmp': [np.nan] * actual_length,
            'dmn': [np.nan] * actual_length
        }, index=close.index)

    try:
        # 2. Native ADX implementation (Wilder's Smoothing) - Resilient to missing TA-Lib
        # Calculate True Range (TR)
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        
        # Calculate Directional Movement (+DM and -DM)
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        plus_dm = pd.Series(0.0, index=close.index)
        plus_dm.loc[(up_move > down_move) & (up_move > 0)] = up_move
        
        minus_dm = pd.Series(0.0, index=close.index)
        minus_dm.loc[(down_move > up_move) & (down_move > 0)] = down_move
        
        # Wilder's Smoothing (EMA with alpha = 1/N)
        alpha = 1.0 / length
        atr = tr.ewm(alpha=alpha, adjust=False, min_periods=length).mean()
        plus_di_smooth = plus_dm.ewm(alpha=alpha, adjust=False, min_periods=length).mean()
        minus_di_smooth = minus_dm.ewm(alpha=alpha, adjust=False, min_periods=length).mean()
        
        plus_di = 100 * (plus_di_smooth / atr)
        minus_di = 100 * (minus_di_smooth / atr)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        adx = dx.ewm(alpha=alpha, adjust=False, min_periods=length).mean()
        
        # 3. Final sanitization (ensure no Inf values that crash JSON)
        def _clean(s):
            return s.replace([np.inf, -np.inf], np.nan)

        return pd.DataFrame({
            'adx': _clean(adx),
            'dmp': _clean(plus_di),
            'dmn': _clean(minus_di)
        }, index=close.index)
        
    except Exception as e:
        logger.error(f"Institutional ADX calculation failed: {e}")
        return pd.DataFrame({
            'adx': [np.nan] * actual_length,
            'dmp': [np.nan] * actual_length,
            'dmn': [np.nan] * actual_length
        }, index=close.index)

def detect_trend_structure(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.DataFrame:
    """
    Detect trend structure and compression (Squeeze) using optimized indicators.
    """
    # Optimized indicators
    adx_df = calculate_adx(high, low, close, length=length)
    
    # BBands using VectorBT
    res_bb = vbt.BBANDS.run(close, window=20, alpha=2)
    bb_upper = res_bb.upper
    bb_lower = res_bb.lower
    bb_width = bb_upper - bb_lower
    
    # KC Implementation using primitives
    kc_mid = calculate_ema(close, span=20)
    # Get ATR using VectorBT
    atr_20 = vbt.ATR.run(high, low, close, window=20).atr
    kc_upper = kc_mid + (2.0 * atr_20)
    kc_lower = kc_mid - (2.0 * atr_20)
    kc_width = kc_upper - kc_lower
    
    # Trend Classifications
    # ADX > 25: Trending, ADX < 20: Range
    structure = pd.Series('Neutral', index=close.index)
    
    # Only assign labels where ADX is not NaN
    adx_values = adx_df['adx']
    valid_adx = adx_values.notna()
    
    structure.loc[valid_adx & (adx_values > 25)] = 'Trending'
    structure.loc[valid_adx & (adx_values < 20)] = 'Range'
    
    # Squeeze condition (Volatility compression)
    # Squeeze occurs when Bollinger Bands are inside Keltner Channels
    is_squeeze = bb_width < kc_width
    
    return pd.DataFrame({
        'structure': structure,
        'is_squeeze': is_squeeze,
        'adx': adx_values
    }, index=close.index)
