import numpy as np
import pandas as pd
from numba import njit
from typing import Dict, List, Any, Tuple
import vectorbt as vbt
from vectorbt.indicators.factory import IndicatorFactory

@njit(cache=True)
def calculate_tpo_nb(high, low, open_time, bin_size, tpo_interval_ns):
    """
    Optimized Numba-accelerated TPO calculation.
    Uses O(num_bins) space instead of O(num_bins * num_brackets).
    """
    price_min = np.min(low)
    price_max = np.max(high)
    
    if price_max == price_min:
        return np.array([price_min]), np.array([1], dtype=np.int64)
        
    num_bins = int(np.ceil((price_max - price_min) / bin_size)) + 1
    
    # Safety Cap to prevent OOM/Hang on bad data
    if num_bins > 50000:
        # If range is too large, we might need a larger bin_size
        return np.zeros(1), np.zeros(1, dtype=np.int64)

    tpo_counts = np.zeros(num_bins, dtype=np.int64)
    last_bracket_seen = np.full(num_bins, -1, dtype=np.int64)
    
    start_time = open_time[0]
    
    for i in range(len(high)):
        bracket_idx = int((open_time[i] - start_time) / tpo_interval_ns)
        
        bin_start = int((low[i] - price_min) / bin_size)
        bin_end = int((high[i] - price_min) / bin_size)
        
        # Clip to safe range
        if bin_start < 0: bin_start = 0
        if bin_end >= num_bins: bin_end = num_bins - 1
        
        for b in range(bin_start, bin_end + 1):
            if last_bracket_seen[b] < bracket_idx:
                tpo_counts[b] += 1
                last_bracket_seen[b] = bracket_idx
                
    price_levels = np.zeros(num_bins)
    for i in range(num_bins):
        price_levels[i] = price_min + (i * bin_size)
        
    return price_levels, tpo_counts

def calculate_market_profile(df: pd.DataFrame, bin_size: float = 0.5, tpo_interval: str = '30min') -> Dict[str, Any]:
    """
    Calculate Market Profile (TPO) for a given DataFrame.
    """
    if df.empty:
        return {}
        
    high = df['high'].values
    low = df['low'].values
    open_time = df.index.values.astype(np.int64)
    
    # Convert interval to nanoseconds
    tpo_interval_ns = pd.Timedelta(tpo_interval).value
    
    levels, counts = calculate_tpo_nb(high, low, open_time, bin_size, tpo_interval_ns)
    
    # POC - Price level with max TPO count
    poc_idx = np.argmax(counts)
    poc = float(levels[poc_idx])
    
    # Value Area (70% of TPOs)
    total_tpos = np.sum(counts)
    va_target = total_tpos * 0.70
    
    # Standard Value Area calculation (Expanding from POC)
    va_sum = counts[poc_idx]
    upper_idx = poc_idx
    lower_idx = poc_idx
    
    while va_sum < va_target:
        # Check two bins above and two bins below
        up_sum = 0
        if upper_idx + 1 < len(counts):
            up_sum += counts[upper_idx + 1]
            if upper_idx + 2 < len(counts):
                up_sum += counts[upper_idx + 2]
                
        down_sum = 0
        if lower_idx - 1 >= 0:
            down_sum += counts[lower_idx - 1]
            if lower_idx - 2 >= 0:
                down_sum += counts[lower_idx - 2]
                
        if up_sum >= down_sum and upper_idx + 1 < len(counts):
            upper_idx += 1
            va_sum += counts[upper_idx]
        elif lower_idx - 1 >= 0:
            lower_idx -= 1
            va_sum += counts[lower_idx]
        else:
            break
            
    val = float(levels[lower_idx])
    vah = float(levels[upper_idx])
    
    return {
        "poc": poc,
        "vah": vah,
        "val": val,
        "profile": {
            "levels": levels.tolist(),
            "counts": counts.tolist()
        }
    }

# --- VectorBT Integration ---

def create_vbt_market_profile():
    """
    Creates a VectorBT Indicator class for Market Profile.
    This allows vectorized application across multiple columns.
    """
    def apply_func(high, low, open_time, bin_size, tpo_interval_ns):
        # Note: IndicatorFactory expects outputs to be same shape as input if not specified
        # Market Profile produces summary stats per column.
        # So we return POC, VAH, VAL as scalars per column.
        
        # We need to handle 2D arrays (columns)
        num_cols = high.shape[1]
        pocs = np.zeros(num_cols)
        vahs = np.zeros(num_cols)
        vals = np.zeros(num_cols)
        
        for c in range(num_cols):
            l, co = calculate_tpo_nb(high[:, c], low[:, c], open_time[:, c], bin_size, tpo_interval_ns)
            
            # Simple metadata extraction inside numba wrapper or here
            # POC
            p_idx = np.argmax(co)
            pocs[c] = l[p_idx]
            
            # Simplified VA for vectorized speed (could reuse logic above)
            # For brevity/safety in apply_func, we'll just return POC for now or implement full VA
            # Full VA implementation is better.
            
            tot = np.sum(co)
            v_target = tot * 0.7
            v_sum = co[p_idx]
            u_i = p_idx
            lo_i = p_idx
            
            while v_sum < v_target:
                u_s = co[u_i+1] if u_i+1 < len(co) else 0
                l_s = co[lo_i-1] if lo_i-1 >= 0 else 0
                if u_s >= l_s and u_i+1 < len(co):
                    u_i += 1
                    v_sum += co[u_i]
                elif lo_i-1 >= 0:
                    lo_i -= 1
                    v_sum += co[lo_i]
                else:
                    break
            vahs[c] = l[u_i]
            vals[c] = l[lo_i]
            
        return pocs, vahs, vals

    return IndicatorFactory(
        class_name='MarketProfile',
        short_name='tpo',
        input_names=['high', 'low', 'open_time'],
        param_names=['bin_size', 'tpo_interval_ns'],
        output_names=['poc', 'vah', 'val']
    ).from_apply_func(
        apply_func,
        bin_size=0.5,
        tpo_interval_ns=1800000000000 # 30m default
    )

TPO_VBT = create_vbt_market_profile()
