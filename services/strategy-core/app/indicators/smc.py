import pandas as pd
import numpy as np
from typing import List, Dict, Any, TypedDict, Optional

# --- Type Definitions ---

class SMCOrderBlock(TypedDict):
    """
    TypedDict for Order Block structure.
    """
    type: str  # 'bullish' | 'bearish'
    index: int
    top: float
    bottom: float
    mitigated: bool
    strength: str  # 'strong' | 'weak'

class SMCFVG(TypedDict):
    """
    TypedDict for Fair Value Gap structure.
    """
    type: str  # 'bullish' | 'bearish'
    index: int
    top: float
    bottom: float
    mitigated: bool

class SMCSweep(TypedDict):
    """
    TypedDict for Liquidity Sweep structure.
    """
    type: str  # 'bullish_sweep' | 'bearish_sweep'
    index: int
    level: float
    description: str

class SMCStructureLabel(TypedDict):
    """
    TypedDict for Market Structure Label (HH, LL, etc.).
    """
    index: int
    text: str
    price: float

class SMCStructure(TypedDict):
    """
    TypedDict for overall Market Structure.
    """
    pivots: List[Dict[str, Any]] 
    labels: List[SMCStructureLabel]
    events: List[Dict[str, Any]]

# --- Detection Logic ---

def detect_order_blocks(ohlc: pd.DataFrame) -> List[SMCOrderBlock]:
    """
    Detect Order Blocks (OB) using Vectorized Vector Operations.
    Bullish OB: Last down candle before a strong up move (impulsive move).
    Bearish OB: Last up candle before a strong down move (impulsive move).
    """
    required_columns = ['open', 'high', 'low', 'close']
    if not all(col in ohlc.columns for col in required_columns):
        return []

    # 1. Pre-calculate Series
    # We need to look at "Previous" (candidate OB) and "Current" (Impulsive Move)
    # So we align everything to the "Current" index (i), referring to i-1 as prev.
    
    close = ohlc['close']
    open_ = ohlc['open']
    
    # Body calculations
    body = (close - open_).abs()
    
    # Previous Candle (i-1)
    prev_close = close.shift(1)
    prev_open = open_.shift(1)
    prev_body = body.shift(1)
    
    # Conditions
    # Bullish OB: Prev Red, Curr Green, Engulfing
    prev_is_red = prev_close < prev_open
    curr_is_green = close > open_
    engulfing_bull = (close > prev_open) & (body > prev_body * 1.5)
    
    bullish_mask = prev_is_red & curr_is_green & engulfing_bull
    
    # Bearish OB: Prev Green, Curr Red, Engulfing
    prev_is_green = prev_close > prev_open
    curr_is_red = close < open_
    engulfing_bear = (close < prev_open) & (body > prev_body * 1.5)
    
    bearish_mask = prev_is_green & curr_is_red & engulfing_bear
    
    # Volume Filter
    has_volume = 'volume' in ohlc.columns
    if has_volume:
        vol = ohlc['volume']
        avg_vol = vol.rolling(window=20).mean()
        # Ensure we have enough data for rolling mean (first 20 will be NaN)
        # Condition: Current Volume > Average Volume
        vol_condition = vol > avg_vol
        
        # We also need i > 20 per original logic (implicit in rolling NaN)
        # Apply filter
        bullish_mask = bullish_mask & vol_condition
        bearish_mask = bearish_mask & vol_condition
    
    # Extract Indices
    # Note: The logic finds the OB at index i-1 based on confirmation at i.
    # So the OB index is actually the index of the detected row MINUS 1.
    
    bull_indices = np.where(bullish_mask)[0]
    bear_indices = np.where(bearish_mask)[0]
    
    obs: List[SMCOrderBlock] = []
    
    # 2. Construct Results (Iteration only on hits, O(Hits) << O(N))
    
    # Vectorized extraction is possible but for List[Dict] return we loop the hits.
    
    for idx in bull_indices:
        # OB is at idx-1
        ob_idx = int(idx - 1)
        if ob_idx < 0: continue
        
        top = float(prev_open.iloc[idx])
        bottom = float(prev_close.iloc[idx])
        
        obs.append({
            "type": "bullish",
            "index": ob_idx,
            "top": top,
            "bottom": bottom,
            "mitigated": False,
            "strength": "strong" if has_volume else "weak" # Since we filter by volume if present
        })
        
    for idx in bear_indices:
        ob_idx = int(idx - 1)
        if ob_idx < 0: continue
        
        top = float(prev_close.iloc[idx])
        bottom = float(prev_open.iloc[idx])
        
        obs.append({
            "type": "bearish",
            "index": ob_idx,
            "top": top,
            "bottom": bottom,
            "mitigated": False,
            "strength": "strong" if has_volume else "weak"
        })
        
    return sorted(obs, key=lambda x: x['index'])

def detect_fvg(ohlc: pd.DataFrame) -> List[SMCFVG]:
    """
    Detect FVG using Vectorization.
    Bullish: Low[i] > High[i-2]
    Bearish: High[i] < Low[i-2]
    """
    low = ohlc['low']
    high = ohlc['high']
    
    # Shifted values
    high_minus_2 = high.shift(2)
    low_minus_2 = low.shift(2)
    
    # Masks
    bull_mask = low > high_minus_2
    bear_mask = high < low_minus_2
    
    # Start from index 2 to avoid garbage comparisons
    # Although Boolean comparison with NaN returns False, explicit is safer
    valid_range = low.index >= low.index[2] 
    # Use array slicing or index logic if index is not numeric? Assuming RangeIndex/Numeric for 'iloc' equivalence
    # But ohlc usually has DatetimeIndex. We will use numeric indices from `np.where`
    
    bull_indices = np.where(bull_mask)[0]
    bear_indices = np.where(bear_mask)[0]
    
    fvgs: List[SMCFVG] = []
    
    # Filter i < 2 manually or trust shift NaNs
    # shift(2) produces NaNs for first 2 rows. Any comparison with NaN is False. 
    # So indices 0 and 1 won't be in the result. Safe.
    
    for idx in bull_indices:
        # FVG is defined by the gap middle candle usually (i-1) or the gap itself
        # Original logic: index = i-1
        gap_idx = int(idx - 1)
        
        top_val = float(low.iloc[idx])
        bottom_val = float(high_minus_2.iloc[idx])
        
        fvgs.append({
            "type": "bullish",
            "index": gap_idx,
            "top": top_val,
            "bottom": bottom_val,
            "mitigated": False
        })
        
    for idx in bear_indices:
        gap_idx = int(idx - 1)
        
        top_val = float(low_minus_2.iloc[idx])
        bottom_val = float(high.iloc[idx])
        
        fvgs.append({
            "type": "bearish",
            "index": gap_idx,
            "top": top_val,
            "bottom": bottom_val,
            "mitigated": False
        })
        
    return sorted(fvgs, key=lambda x: x['index'])

def detect_liquidity_sweeps(ohlc: pd.DataFrame) -> List[SMCSweep]:
    """
    Detect Sweeps using Vectorization.
    """
    window = 5
    high = ohlc['high']
    low = ohlc['low']
    close = ohlc['close']
    
    # 1. Recent Highs/Lows (Looking back 'window' bars EXCLUDING current)
    # We use shift(1) to move window back by 1 step so it doesn't include current bar
    recent_highs = high.shift(1).rolling(window=window).max()
    recent_lows = low.shift(1).rolling(window=window).min()
    
    # 2. Conditions
    # Bearish Sweep: High > Recent High AND Close < Recent High
    bear_sweep_mask = (high > recent_highs) & (close < recent_highs)
    
    # Bullish Sweep: Low < Recent Low AND Close > Recent Low
    bull_sweep_mask = (low < recent_lows) & (close > recent_lows)
    
    sweeps: List[SMCSweep] = []
    
    bear_indices = np.where(bear_sweep_mask)[0]
    bull_indices = np.where(bull_sweep_mask)[0]
    
    for idx in bear_indices:
        level = float(recent_highs.iloc[idx])
        sweeps.append({
            "type": "bearish_sweep",
            "index": int(idx),
            "level": level,
            "description": "Swept recent high and closed below"
        })
        
    for idx in bull_indices:
        level = float(recent_lows.iloc[idx])
        sweeps.append({
            "type": "bullish_sweep",
            "index": int(idx),
            "level": level,
            "description": "Swept recent low and closed above"
        })
        
    return sorted(sweeps, key=lambda x: x['index'])

def detect_structure(ohlc: pd.DataFrame, window: int = 5) -> SMCStructure:
    """
    Detect Structure using Rolling Window Vectorization (Local Max/Min).
    """
    if len(ohlc) < window * 2:
        return SMCStructure(pivots=[], labels=[], events=[])

    high = ohlc['high']
    low = ohlc['low']
    
    # 1. Local Maxima/Minima detection
    # A point i is a max if high[i] == max(high[i-w : i+w+1])
    # We use centered rolling window
    
    # Note: shift(-window) is not strictly possible with standard rolling unless we use 'center=True'
    # Rolling center=True looks at [i-w, i+w] roughly.
    # window size for lookback w and lookforward w is 2*w + 1
    
    roll_window = 2 * window + 1
    
    # rolling max (centered)
    local_max = high.rolling(window=roll_window, center=True).max()
    local_min = low.rolling(window=roll_window, center=True).min()
    
    # Identifying Pivots
    # Pivot High: High == Local Max
    # Pivot Low: Low == Local Min
    # Note: 'center=True' in pandas might result in NaN at tail/head correctly.
    
    is_pivot_high = (high == local_max)
    is_pivot_low = (low == local_min)
    
    # Extract
    pivot_high_indices = np.where(is_pivot_high)[0]
    pivot_low_indices = np.where(is_pivot_low)[0]
    
    pivots: List[Dict[str, Any]] = []
    
    for idx in pivot_high_indices:
        pivots.append({"index": int(idx), "type": "high", "price": float(high.iloc[idx])})
        
    for idx in pivot_low_indices:
        pivots.append({"index": int(idx), "type": "low", "price": float(low.iloc[idx])})
        
    pivots.sort(key=lambda x: x['index'])
    
    structure: SMCStructure = {
        "pivots": pivots,
        "labels": [],
        "events": []
    }
    
    # Label HH/LL - Linear pass is required as it's stateful (depends on previous pivot)
    # This is O(P) where P is number of pivots << N candles. Fast enough.
    
    if len(pivots) > 1:
        last_high = None
        last_low = None
        
        for p in pivots:
            if p["type"] == "high":
                label = "H"
                if last_high:
                    label = "HH" if p["price"] > last_high["price"] else "LH"
                structure["labels"].append({"index": p["index"], "text": label, "price": p["price"]})
                last_high = p
            else:
                label = "L"
                if last_low:
                    label = "LL" if p["price"] < last_low["price"] else "HL"
                structure["labels"].append({"index": p["index"], "text": label, "price": p["price"]})
                last_low = p

    return structure

def calculate_auto_fibs(ohlc: pd.DataFrame, window: int = 100) -> Dict[str, float]:
    """
    Calculate Fib levels.
    """
    if len(ohlc) < 2: return {}
    
    recent = ohlc.iloc[-window:] if len(ohlc) > window else ohlc
    high_val = float(recent['high'].max())
    low_val = float(recent['low'].min())
    diff = high_val - low_val
    
    if diff == 0: return {}
    
    return {
        "0.0": low_val,
        "0.236": low_val + diff * 0.236,
        "0.382": low_val + diff * 0.382,
        "0.5": low_val + diff * 0.5,
        "0.618": low_val + diff * 0.618,
        "0.786": low_val + diff * 0.786,
        "1.0": high_val
    }
