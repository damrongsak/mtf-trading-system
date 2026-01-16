import pandas as pd
import numpy as np
import vectorbt as vbt
from numba import njit
from vectorbt.indicators.factory import IndicatorFactory

def calculate_ema(close: pd.Series, span: int) -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA).
    """
    return close.ewm(span=span, adjust=False).mean()

# --- Numba Compiled ADX Calculation Logic (VectorBT) ---

@njit(cache=True)
def get_tr_nb(high, low, close):
    """Calculate True Range."""
    tr = np.zeros_like(close)
    rows, cols = close.shape
    for c in range(cols):
        tr[0, c] = high[0, c] - low[0, c]
        for i in range(1, rows):
            h = high[i, c]
            l = low[i, c]
            cp = close[i-1, c]
            val1 = h - l
            val2 = np.abs(h - cp)
            val3 = np.abs(l - cp)
            tr[i, c] = max(val1, max(val2, val3))
    return tr

@njit(cache=True)
def get_dm_nb(high, low):
    """Calculate +DM and -DM."""
    rows, cols = high.shape
    plus_dm = np.zeros_like(high)
    minus_dm = np.zeros_like(high)
    for c in range(cols):
        for i in range(1, rows):
            up_move = high[i, c] - high[i-1, c]
            down_move = low[i-1, c] - low[i, c]
            if up_move > down_move and up_move > 0:
                plus_dm[i, c] = up_move
            if down_move > up_move and down_move > 0:
                minus_dm[i, c] = down_move
    return plus_dm, minus_dm

@njit(cache=True)
def wilders_nodes_nb(a, length):
    """Wilder's Smoothing (alpha=1/length)."""
    rows, cols = a.shape
    out = np.full_like(a, np.nan)
    alpha = 1.0 / length
    for c in range(cols):
        run_sum = 0.0
        nan_count = 0
        for i in range(length):
            if not np.isnan(a[i, c]):
                run_sum += a[i, c]
            else:
                nan_count += 1
        
        # Simple Mean Initialization
        if nan_count == 0:
             out[length-1, c] = run_sum / length 
        
        for i in range(length, rows):
            prev = out[i-1, c]
            curr = a[i, c]
            if np.isnan(prev):
                 if i == length-1 and nan_count == 0: pass # Handled above
                 elif i >= length and not np.isnan(curr):
                     # Try lazy init if simple mean failed? 
                     # For standard wilder, we need strict N periods.
                     pass 
            else:
                 if not np.isnan(curr):
                     out[i, c] = prev + alpha * (curr - prev)
                 else:
                     out[i, c] = prev # Carrier forward? Or Nan? Standard is usually break.
                     
    return out

@njit(cache=True)
def adx_apply_nb(high, low, close, length):
    """Main ADX Calculation function for IndicatorFactory."""
    tr = get_tr_nb(high, low, close)
    p_dm, m_dm = get_dm_nb(high, low)
    
    s_tr = wilders_nodes_nb(tr, length)
    s_p_dm = wilders_nodes_nb(p_dm, length)
    s_m_dm = wilders_nodes_nb(m_dm, length)
    
    s_tr_safe = np.where(s_tr == 0, np.nan, s_tr)
    p_di = 100 * s_p_dm / s_tr_safe
    m_di = 100 * s_m_dm / s_tr_safe
    
    di_sum = p_di + m_di
    di_diff = np.abs(p_di - m_di)
    dx = 100 * di_diff / np.where(di_sum == 0, np.nan, di_sum)
    
    adx = wilders_nodes_nb(dx, length)
    return adx, p_di, m_di

# --- Indicator Factory ---
ADX_VBT = IndicatorFactory(
    class_name='ADX',
    short_name='adx',
    input_names=['high', 'low', 'close'],
    param_names=['length'],
    output_names=['adx', 'plus_di', 'minus_di'],
).from_apply_func(
    adx_apply_nb,
    length=14
)

def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.DataFrame:
    """
    Calculate ADX using high-performance VectorBT (Numba).
    Returns DataFrame with columns: adx, dmp, dmn
    """
    # VBT handles Series inputs automatically
    res = ADX_VBT.run(high, low, close, length=length)
    
    return pd.DataFrame({
        'adx': res.adx,
        'dmp': res.plus_di,
        'dmn': res.minus_di
    }, index=close.index)
