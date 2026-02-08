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
    timestamp: str # ISO string for charting
    top: float
    bottom: float
    mitigated: bool
    strength: str  # 'strong' | 'weak'
    meta: Dict[str, Any]

class SMCFVG(TypedDict):
    """
    TypedDict for Fair Value Gap structure.
    """
    type: str  # 'bullish' | 'bearish'
    index: int
    timestamp: str 
    top: float
    bottom: float
    mitigated: bool
    meta: Dict[str, Any]

class SMCSweep(TypedDict):
    """
    TypedDict for Liquidity Sweep structure.
    """
    type: str  # 'bullish_sweep' | 'bearish_sweep'
    index: int
    timestamp: str
    level: float
    description: str
    meta: Dict[str, Any]

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
        
        timestamp = ohlc.index[ob_idx]
        ts_str = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
        
        top = float(prev_open.iloc[idx])
        bottom = float(prev_close.iloc[idx])
        
        obs.append({
            "type": "bullish",
            "index": ob_idx,
            "timestamp": ts_str,
            "top": top,
            "bottom": bottom,
            "mitigated": False,
            "strength": "strong" if has_volume else "weak",
            "meta": {
                "body_size": float(prev_body.iloc[idx]),
                "engulfing_ratio": float(body.iloc[idx] / prev_body.iloc[idx]) if prev_body.iloc[idx] > 0 else 0
            }
        })
        
    for idx in bear_indices:
        ob_idx = int(idx - 1)
        if ob_idx < 0: continue
        
        timestamp = ohlc.index[ob_idx]
        ts_str = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
        
        top = float(prev_close.iloc[idx])
        bottom = float(prev_open.iloc[idx])
        
        obs.append({
            "type": "bearish",
            "index": ob_idx,
            "timestamp": ts_str,
            "top": top,
            "bottom": bottom,
            "mitigated": False,
            "strength": "strong" if has_volume else "weak",
            "meta": {
                "body_size": float(prev_body.iloc[idx]),
                "engulfing_ratio": float(body.iloc[idx] / prev_body.iloc[idx]) if prev_body.iloc[idx] > 0 else 0
            }
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
        
        timestamp = ohlc.index[gap_idx]
        ts_str = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
        
        top_val = float(low.iloc[idx])
        bottom_val = float(high_minus_2.iloc[idx])
        
        fvgs.append({
            "type": "bullish",
            "index": gap_idx,
            "timestamp": ts_str,
            "top": top_val,
            "bottom": bottom_val,
            "mitigated": False,
            "meta": {
                "gap_size": float(top_val - bottom_val)
            }
        })
        
    for idx in bear_indices:
        gap_idx = int(idx - 1)
        
        timestamp = ohlc.index[gap_idx]
        ts_str = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
        
        top_val = float(low_minus_2.iloc[idx])
        bottom_val = float(high.iloc[idx])
        
        fvgs.append({
            "type": "bearish",
            "index": gap_idx,
            "timestamp": ts_str,
            "top": top_val,
            "bottom": bottom_val,
            "mitigated": False,
            "meta": {
                "gap_size": float(top_val - bottom_val)
            }
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
        timestamp = ohlc.index[idx]
        ts_str = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
        
        sweeps.append({
            "type": "bearish_sweep",
            "index": int(idx),
            "timestamp": ts_str,
            "level": level,
            "description": "Swept recent high and closed below",
            "meta": {
                "swept_level": level,
                "wick_size": float(high.iloc[idx] - recent_highs.iloc[idx])
            }
        })
        
    for idx in bull_indices:
        level = float(recent_lows.iloc[idx])
        timestamp = ohlc.index[idx]
        ts_str = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
        
        sweeps.append({
            "type": "bullish_sweep",
            "index": int(idx),
            "timestamp": ts_str,
            "level": level,
            "description": "Swept recent low and closed above",
            "meta": {
                "swept_level": level,
                "wick_size": float(recent_lows.iloc[idx] - low.iloc[idx])
            }
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
        "0.65": low_val + diff * 0.65,
        "0.705": low_val + diff * 0.705,
        "0.786": low_val + diff * 0.786,
        "0.886": low_val + diff * 0.886,
        "1.0": high_val,
        "1.13": low_val + diff * 1.13,
        "1.272": low_val + diff * 1.272,
        "1.414": low_val + diff * 1.414,
        "1.618": low_val + diff * 1.618,
        "2.0": low_val + diff * 2.0,
        "2.618": low_val + diff * 2.618,
        "3.618": low_val + diff * 3.618,
        "4.236": low_val + diff * 4.236
    }

def analyze_smc(df: pd.DataFrame, symbol: str = "Unknown") -> Dict[str, Any]:
    """
    Central orchestration for all SMC indicators and metadata.
    Includes Institutional Bias and Strategic Reasoning.
    """
    from datetime import datetime
    
    if df.empty:
        return {
            "order_blocks": [], "fvgs": [], "liquidity_sweeps": [], 
            "structure": {}, "auto_fibs": {}, 
            "institutional_bias": "NEUTRAL", "strategic_reasoning": "Insufficient data",
            "timestamp": datetime.utcnow().isoformat(), "meta": {}
        }

    obs = detect_order_blocks(df)
    fvgs = detect_fvg(df)
    sweeps = detect_liquidity_sweeps(df)
    structure = detect_structure(df)
    fibs = calculate_auto_fibs(df)
    
    last_close = float(df['close'].iloc[-1])
    
    # --- Institutional Reasoning & Bias ---
    # Bias is determined by proximity to unmitigated institutional levels
    bias = "NEUTRAL"
    reasoning = "Market is currently in safe-haven consolidation."
    
    # Proximity tolerance: 0.1% for Gold ($4000+ means ~$4.0 range)
    tolerance = 0.001 
    
    bullish_confluence = []
    bearish_confluence = []
    
    # 1. Check Order Blocks
    unmitigated_obs = [ob for ob in obs if not ob.get("mitigated")]
    for ob in reversed(unmitigated_obs):
        if ob["type"] == "bullish":
            # Support zone
            if ob["bottom"] <= last_close <= ob["top"] * (1 + tolerance):
                bias = "BULLISH"
                reasoning = f"Price reacting to significant Bullish Order Block at {ob['top']}."
                bullish_confluence.append("OB_SUPPORT")
                break
        else:
            # Resistance zone
            if ob["bottom"] * (1 - tolerance) <= last_close <= ob["top"]:
                bias = "BEARISH"
                reasoning = f"Price rejecting significant Bearish Order Block at {ob['bottom']}."
                bearish_confluence.append("OB_RESISTANCE")
                break

    # 2. Check FVGs for Confluence
    unmitigated_fvgs = [f for f in fvgs if not f.get("mitigated")]
    for fvg in reversed(unmitigated_fvgs):
        if fvg["type"] == "bullish":
            if fvg["bottom"] <= last_close <= fvg["top"] * (1 + tolerance):
                if bias == "BULLISH":
                    reasoning += f" Confluence found with Bullish FVG (Gap: {fvg.get('meta',{}).get('gap_size',0):.2f})."
                    bullish_confluence.append("FVG_CONFLUENCE")
                elif bias == "NEUTRAL":
                    bias = "BULLISH"
                    reasoning = f"Price filling Bullish FVG at {fvg['bottom']}."
                break
        else:
            if fvg["bottom"] * (1 - tolerance) <= last_close <= fvg["top"]:
                if bias == "BEARISH":
                    reasoning += f" Confluence found with Bearish FVG (Gap: {fvg.get('meta',{}).get('gap_size',0):.2f})."
                    bearish_confluence.append("FVG_CONFLUENCE")
                elif bias == "NEUTRAL":
                    bias = "BEARISH"
                    reasoning = f"Price filling Bearish FVG at {fvg['top']}."
                break

    # 3. Check Sweeps
    if sweeps:
        last_sweep = sweeps[-1]
        if last_sweep["type"] == "bullish_sweep" and last_sweep["index"] >= len(df) - 5:
            reasoning = f"Liquidity Sweep detected at {last_sweep['level']}. Institutional accumulation likely."
            bias = "BULLISH"
        elif last_sweep["type"] == "bearish_sweep" and last_sweep["index"] >= len(df) - 5:
            reasoning = f"Liquidity Sweep detected at {last_sweep['level']}. Institutional distribution likely."
            bias = "BEARISH"

    # Enhanced Metadata
    meta = {
        "symbol": symbol,
        "candle_count": len(df),
        "volatility_score": float(df['high'].max() - df['low'].min()) / float(df['close'].iloc[-1]) if not df.empty else 0,
        "bullish_confluence": bullish_confluence,
        "bearish_confluence": bearish_confluence
    }
    
    return {
        "order_blocks": obs,
        "fvgs": fvgs,
        "liquidity_sweeps": sweeps,
        "structure": structure,
        "auto_fibs": fibs,
        "institutional_bias": bias,
        "strategic_reasoning": reasoning,
        "timestamp": datetime.utcnow().isoformat(),
        "meta": meta
    }
