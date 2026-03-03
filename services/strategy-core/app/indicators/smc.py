from __future__ import annotations
from typing import List, Dict, Any, TypedDict, Optional
# Heavy imports moved inside functions to prevent hang during registration initialization
# import pandas as pd
# import numpy as np

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

class SMCInducement(TypedDict):
    """
    TypedDict for Inducement (IDM) signals.
    """
    type: str  # 'buy_side' | 'sell_side'
    index: int
    timestamp: str
    price: float
    level: float
    meta: Dict[str, Any]

class SMCStructure(TypedDict):
    """
    TypedDict for overall Market Structure.
    """
    pivots: List[Dict[str, Any]] 
    labels: List[SMCStructureLabel]
    events: List[Dict[str, Any]]
    inducements: List[SMCInducement]

# --- Detection Logic ---

def detect_order_blocks(ohlc: pd.DataFrame) -> List[SMCOrderBlock]:
    import pandas as pd
    import numpy as np
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
    
    close = pd.to_numeric(ohlc['close'], errors='coerce')
    open_ = pd.to_numeric(ohlc['open'], errors='coerce')
    
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
    import pandas as pd
    import numpy as np
    """
    Detect FVG using Vectorization.
    Bullish: Low[i] > High[i-2]
    Bearish: High[i] < Low[i-2]
    """
    low = pd.to_numeric(ohlc['low'], errors='coerce')
    high = pd.to_numeric(ohlc['high'], errors='coerce')
    
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
    import pandas as pd
    import numpy as np
    """
    Detect Sweeps using Vectorization.
    """
    window = 5
    high = pd.to_numeric(ohlc['high'], errors='coerce')
    low = pd.to_numeric(ohlc['low'], errors='coerce')
    close = pd.to_numeric(ohlc['close'], errors='coerce')
    
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

def detect_inducement(df: pd.DataFrame, lookback: int = 20, vol_ma_period: int = 20) -> List[SMCInducement]:
    import pandas as pd
    import numpy as np
    from app.indicators.momentum import calculate_rsi
    
    """
    Vectorized detection of Inducement (IDM) traps.
    """
    if len(df) < lookback + 1:
        return []

    high = pd.to_numeric(df['high'], errors='coerce')
    low = pd.to_numeric(df['low'], errors='coerce')
    close = pd.to_numeric(df['close'], errors='coerce')
    open_ = pd.to_numeric(df['open'], errors='coerce')
    volume = pd.to_numeric(df['volume'], errors='coerce')
    
    # 1. RSI and Divergence Context
    rsi = calculate_rsi(close)
    
    # 2. Liquidity Zones (Recent Extremes)
    recent_high = high.shift(1).rolling(window=lookback).max()
    recent_low = low.shift(1).rolling(window=lookback).min()
    recent_rsi_high = rsi.shift(1).rolling(window=lookback).max()
    recent_rsi_low = rsi.shift(1).rolling(window=lookback).min()
    
    # 3. Candle Anatomy
    body_size = (close - open_).abs()
    
    # Upper Wick: high - max(open, close)
    upper_wick = high - df[['open', 'close']].max(axis=1)
    # Lower Wick: min(open, close) - low
    lower_wick = df[['open', 'close']].min(axis=1) - low
    
    # Avoid division by zero for total size
    total_size = high - low
    
    # Rejection definition: Wick > 2 * Body
    has_long_upper_wick = upper_wick > (2 * body_size)
    has_long_lower_wick = lower_wick > (2 * body_size)
    
    # 4. Volume Confirmation
    avg_vol = volume.rolling(window=vol_ma_period).mean()
    unusual_volume = volume > (avg_vol * 1.5)
    
    # 5. Divergence & Fakeout Logic
    # Bearish IDM (Trap for Buyers)
    is_fake_breakout_high = (high > recent_high) & (close < recent_high)
    bearish_divergence = (high > recent_high) & (rsi < recent_rsi_high)
    
    buy_side_mask = is_fake_breakout_high & has_long_upper_wick & unusual_volume & bearish_divergence
    
    # Bullish IDM (Trap for Sellers)
    is_fake_breakdown_low = (low < recent_low) & (close > recent_low)
    bullish_divergence = (low < recent_low) & (rsi > recent_rsi_low)
    
    sell_side_mask = is_fake_breakdown_low & has_long_lower_wick & unusual_volume & bullish_divergence
    
    # 6. Extract Indices and Build Results
    idms: List[SMCInducement] = []
    
    buy_indices = np.where(buy_side_mask)[0]
    sell_indices = np.where(sell_side_mask)[0]
    
    for idx in buy_indices:
        timestamp = df.index[idx]
        ts_str = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
        idms.append({
            "type": "buy_side",
            "index": int(idx),
            "timestamp": ts_str,
            "price": float(close.iloc[idx]),
            "level": float(recent_high.iloc[idx]),
            "meta": {
                "wick_ratio": float(upper_wick.iloc[idx] / body_size.iloc[idx]) if body_size.iloc[idx] > 0 else 0,
                "volume_ratio": float(volume.iloc[idx] / avg_vol.iloc[idx]) if avg_vol.iloc[idx] > 0 else 0,
                "rsi_value": float(rsi.iloc[idx])
            }
        })
        
    for idx in sell_indices:
        timestamp = df.index[idx]
        ts_str = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
        idms.append({
            "type": "sell_side",
            "index": int(idx),
            "timestamp": ts_str,
            "price": float(close.iloc[idx]),
            "level": float(recent_low.iloc[idx]),
            "meta": {
                "wick_ratio": float(lower_wick.iloc[idx] / body_size.iloc[idx]) if body_size.iloc[idx] > 0 else 0,
                "volume_ratio": float(volume.iloc[idx] / avg_vol.iloc[idx]) if avg_vol.iloc[idx] > 0 else 0,
                "rsi_value": float(rsi.iloc[idx])
            }
        })
        
    return sorted(idms, key=lambda x: x['index'])

def detect_structure(ohlc: pd.DataFrame, window: int = 2) -> SMCStructure:
    import pandas as pd
    import numpy as np
    """
    Detect Structure using Rolling Window Vectorization (Lagging, Non-Repainting).
    """
    if len(ohlc) < window * 2 + 1:
        return SMCStructure(pivots=[], labels=[], events=[], inducements=[])

    high = ohlc['high']
    low = ohlc['low']
    
    # 1. Non-repainting pivot detection (Lagging by `window` bars)
    # A point i is a max if it's strictly greater than `window` bars before and after it.
    # We evaluate at index `i` (current bar), looking back to `i - 2*window`.
    # The pivot itself is at `i - window`.
    
    # left_max evaluates [i - 2*window, i - window - 1]
    left_max = high.shift(window + 1).rolling(window=window).max()
    
    # right_max evaluates [i - window + 1, i]
    # Note: rolling(window) includes the current bar, so it looks back `window - 1` bars.
    # We want [i - window + 1, i], which is exactly `window` bars ending at `i`.
    right_max = high.rolling(window=window).max()
    
    # center is the bar at `i - window`
    center_high = high.shift(window)
    
    # Condition: center > left and center > right
    is_pivot_high = (center_high > left_max) & (center_high > right_max)
    
    # Same for lows
    left_min = low.shift(window + 1).rolling(window=window).min()
    right_min = low.rolling(window=window).min()
    center_low = low.shift(window)
    
    is_pivot_low = (center_low < left_min) & (center_low < right_min)
    
    # Extract indices. The boolean masks align with index `i`.
    # The actual pivot occurred at `i - window`.
    pivot_high_eval_indices = np.where(is_pivot_high)[0]
    pivot_low_eval_indices = np.where(is_pivot_low)[0]
    
    pivots: List[Dict[str, Any]] = []
    
    for idx_eval in pivot_high_eval_indices:
        idx_pivot = int(idx_eval - window)
        if idx_pivot < 0: continue
        pivots.append({"index": idx_pivot, "type": "high", "price": float(high.iloc[idx_pivot])})
        
    for idx_eval in pivot_low_eval_indices:
        idx_pivot = int(idx_eval - window)
        if idx_pivot < 0: continue
        pivots.append({"index": idx_pivot, "type": "low", "price": float(low.iloc[idx_pivot])})
        
    pivots.sort(key=lambda x: x['index'])
    
    structure: SMCStructure = {
        "pivots": pivots,
        "labels": [],
        "events": [],
        "inducements": []
    }
    
    # Label HH/LL - Linear pass is required as it's stateful (depends on previous pivot)
    # This is O(P) where P is number of pivots << N candles. Fast enough.
    
    # Label HH/LL and Detect MSS
    if len(pivots) > 0:
        last_high = None
        last_low = None
        
        # We also want to track the *confirmed* structure to detect shifts
        # Simple MSS: 
        # Bullish MSS: Price closes above the last Lower High (LH)
        # Bearish MSS: Price closes below the last Higher Low (HL)
        
        # To do this correctly in a vectorized/batch way is complex.
        # We will iterate pivots to label them, then check for breaks.
        
        # 1. Label Pivots
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

        # 2. Detect MSS (Events)
        # We scan the price array and check when it crosses the *most recent* contrarian pivot
        # Optimization: limit to recent history or significant pivots?
        # For this implementation, we will look for 'ChoCh' (Change of Character)
        # A ChoCh is the first internal structure break.
        
        # Find the last LH and last HL
        highs = [p for p in structure["labels"] if p["text"] in ["H", "HH", "LH"]]
        lows = [p for p in structure["labels"] if p["text"] in ["L", "LL", "HL"]]
        
        if highs and lows:
            # We only check for MSS in the most recent candles (last 50?) to keep it relevant
            # This Avoids scanning the whole history for old MSS
            scan_start = max(0, len(ohlc) - 50)
            recent_highs = [h for h in highs if h["index"] < len(ohlc) - 1] # Valid completed pivots
            recent_lows = [l for l in lows if l["index"] < len(ohlc) - 1]
            
            if recent_highs:
                last_major_high = recent_highs[-1]
                # Bullish MSS: Close > Last High
                # We check candles AFTER the last high
                for i in range(last_major_high["index"] + 1, len(ohlc)):
                    if ohlc['close'].iloc[i] > last_major_high["price"]:
                        structure["events"].append({
                            "type": "mss_bullish",
                            "index": i,
                            "price": float(ohlc['close'].iloc[i]),
                            "trigger_pivot": last_major_high
                        })
                        break # Only report the first break (Change of Character)

            if recent_lows:
                last_major_low = recent_lows[-1]
                # Bearish MSS: Close < Last Low
                for i in range(last_major_low["index"] + 1, len(ohlc)):
                    if ohlc['close'].iloc[i] < last_major_low["price"]:
                        structure["events"].append({
                            "type": "mss_bearish",
                            "index": i,
                            "price": float(ohlc['close'].iloc[i]),
                            "trigger_pivot": last_major_low
                        })
                        break
    
    structure["inducements"] = detect_inducement(ohlc)
    
    return structure

def calculate_auto_fibs(ohlc: pd.DataFrame, window: int = 100) -> Dict[str, float]:
    import pandas as pd
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
        "1.0": high_val,
    }

def generate_setups(df: pd.DataFrame, obs: List[SMCOrderBlock], fvgs: List[SMCFVG], symbol: str = "Unknown") -> List[Dict[str, Any]]:
    import pandas as pd
    import numpy as np
    """
    Generate actionable trade setups based on SMC levels.
    """
    if df.empty: return []
    
    last_close = float(df['close'].iloc[-1])
    setups = []
    
    # 1. Calculate ATR for structural offsets
    if len(df) >= 14:
        # Standard ATR
        tr = pd.concat([
            (df['high'] - df['low']),
            (df['high'] - df['close'].shift(1)).abs(),
            (df['low'] - df['close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = float(tr.rolling(window=14).mean().iloc[-1])
    else:
        atr = last_close * 0.001 # 0.1% volatility fallback
        
    # 2. Extract unmitigated institutional zones
    unmitigated_obs = [ob for ob in obs if not ob.get("mitigated", False)]
    
    is_gold = "XAU" in symbol.upper()
    
    # 3. Process Bullish Setups (Buy Zones)
    # Volatility-Adjusted 100% Stop Loss Buffer
    sl_buffer = atr * 0.5
    
    for ob in unmitigated_obs:
        if ob["type"] == "bullish":
            entry = ob["top"]
            # Structural SL below OB bottom with Volatility-Adjusted buffer
            sl = ob["bottom"] - sl_buffer 
            
            # Initial Target: 2.0 RR or next Bearish OB
            tp = entry + (entry - sl) * 2.0
            
            # Refine TP with Bearish OB resistance
            bear_obs = [b for b in obs if b["type"] == "bearish" and b["bottom"] > entry]
            if bear_obs:
                # Target the nearest Bearish OB
                tp = bear_obs[0]["bottom"]
            
            rr = (tp - entry) / (entry - sl) if (entry - sl) > 0 else 0
            
            if rr >= 1.5:
                setups.append({
                    "id": f"SMC_LONG_{ob['index']}",
                    "type": "LONG",
                    "reason": f"Structural Bullish OB at {ob['top']:.2f}",
                    "entry": round(entry, 2 if is_gold else 5),
                    "stop_loss": round(sl, 2 if is_gold else 5),
                    "take_profit": round(tp, 2 if is_gold else 5),
                    "rr": round(rr, 2),
                    "status": "POTENTIAL" if last_close > entry else "ACTIVE"
                })

    # 4. Process Bearish Setups (Sell Zones)
    for ob in unmitigated_obs:
        if ob["type"] == "bearish":
            entry = ob["bottom"]
            # Structural SL above OB top with Volatility-Adjusted buffer
            sl = ob["top"] + sl_buffer
            
            tp = entry - (sl - entry) * 2.0
            
            # Refine TP with Bullish OB support
            bull_obs = [b for b in obs if b["type"] == "bullish" and b["top"] < entry]
            if bull_obs:
                # Target the nearest Bullish OB below us (which is the last one in the sorted list)
                tp = bull_obs[-1]["top"]
                
            rr = (entry - tp) / (sl - entry) if (sl - entry) > 0 else 0
            
            if rr >= 1.5:
                setups.append({
                    "id": f"SMC_SHORT_{ob['index']}",
                    "type": "SHORT",
                    "reason": f"Structural Bearish OB at {ob['bottom']:.2f}",
                    "entry": round(entry, 2 if is_gold else 5),
                    "stop_loss": round(sl, 2 if is_gold else 5),
                    "take_profit": round(tp, 2 if is_gold else 5),
                    "rr": round(rr, 2),
                    "status": "POTENTIAL" if last_close < entry else "ACTIVE"
                })
                
    return setups

def analyze_smc(df: pd.DataFrame, symbol: str = "Unknown", timeframe: str = "H1") -> Dict[str, Any]:
    import pandas as pd
    """
    Central orchestration for all SMC indicators and metadata.
    Includes Institutional Bias and Strategic Reasoning.
    """
    from datetime import datetime
    
    if df.empty:
        return {
            "order_blocks": [], "fvgs": [], "liquidity_sweeps": [], 
            "structure": {}, "auto_fibs": {}, "inducement_signals": [],
            "institutional_bias": "NEUTRAL", "strategic_reasoning": "Insufficient data",
            "timestamp": datetime.utcnow().isoformat(), "timeframe": timeframe, "meta": {}
        }

    obs = detect_order_blocks(df)
    fvgs = detect_fvg(df)
    sweeps = detect_liquidity_sweeps(df)
    # Use a dynamic N based on timeframe if available, otherwise default to 2
    structure_window = 2
    if timeframe in ["M1", "M5", "M15"]:
        structure_window = 3
        
    structure = detect_structure(df, window=structure_window)
    idms = detect_inducement(df)
    fibs = calculate_auto_fibs(df)
    setups = generate_setups(df, obs, fvgs, symbol)
    
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
        "timeframe": timeframe,
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
        "inducement_signals": idms,
        "setups": setups,
        "auto_fibs": fibs,
        "institutional_bias": bias,
        "strategic_reasoning": reasoning,
        "timestamp": datetime.utcnow().isoformat(),
        "timeframe": timeframe,
        "meta": meta
    }
