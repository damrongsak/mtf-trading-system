import pandas as pd
import numpy as np

# Lazy loading cache
_ADX_VBT_STUB = None

def get_adx_vbt():
    global _ADX_VBT_STUB
    if _ADX_VBT_STUB is None:
        from numba import njit
        from vectorbt.indicators.factory import IndicatorFactory

        @njit(cache=False)
        def get_tr_nb(high, low, close):
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

        @njit(cache=False)
        def get_dm_nb(high, low):
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

        @njit(cache=False)
        def wilders_nodes_nb(a, length):
            rows, cols = a.shape
            out = np.full_like(a, np.nan)
            alpha = 1.0 / length
            
            for c in range(cols):
                run_sum = 0.0
                valid_count = 0
                initialized = False
                
                for i in range(rows):
                    curr = a[i, c]
                    if np.isnan(curr):
                        continue
                    
                    if not initialized:
                        run_sum += curr
                        valid_count += 1
                        if valid_count == length:
                            out[i, c] = run_sum / length
                            initialized = True
                    else:
                        prev = out[i-1, c]
                        out[i, c] = prev + alpha * (curr - prev)
                             
            return out

        @njit(cache=False)
        def adx_apply_nb(high, low, close, length):
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

        _ADX_VBT_STUB = IndicatorFactory(
            class_name='ADX',
            short_name='adx',
            input_names=['high', 'low', 'close'],
            param_names=['length'],
            output_names=['adx', 'plus_di', 'minus_di'],
        ).from_apply_func(
            adx_apply_nb,
            length=14
        )
    return _ADX_VBT_STUB

def calculate_ema(close: pd.Series, span: int) -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA).
    """
    return close.ewm(span=span, adjust=False).mean()

def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.DataFrame:
    """
    Calculate ADX using high-performance VectorBT (Numba).
    Returns DataFrame with columns: adx, dmp, dmn
    """
    adx_vbt = get_adx_vbt()
    res = adx_vbt.run(high, low, close, length=length)
    
    return pd.DataFrame({
        'adx': res.adx,
        'dmp': res.plus_di,
        'dmn': res.minus_di
    }, index=close.index)

def detect_trend_structure(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.DataFrame:
    """
    Detect trend structure and compression.
    """
    import vectorbt as vbt
    adx_df = calculate_adx(high, low, close, length=length)
    
    # BBands
    res_bb = vbt.BBANDS.run(close, window=20, alpha=2)
    bb_width = res_bb.upper - res_bb.lower
    
    # KC (Manual Implementation using primitives)
    kc_mid = calculate_ema(close, span=20)
    atr_20 = vbt.ATR.run(high, low, close, window=20).atr
    kc_upper = kc_mid + (2.0 * atr_20)
    kc_lower = kc_mid - (2.0 * atr_20)
    kc_width = kc_upper - kc_lower
    
    # Conditions
    is_trend = adx_df['adx'] > 25
    is_range = adx_df['adx'] < 20
    is_squeeze = bb_width < kc_width
    
    structure = pd.Series('Neutral', index=close.index)
    structure.loc[is_trend] = 'Trending'
    structure.loc[is_range] = 'Range'
    
    return pd.DataFrame({
        'structure': structure,
        'is_squeeze': is_squeeze,
        'adx': adx_df['adx']
    }, index=close.index)
