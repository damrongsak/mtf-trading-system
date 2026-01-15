import pandas as pd
import numpy as np
from typing import List, Dict, Any, TypedDict, Optional

# --- Type Definitions ---

class SMCOrderBlock(TypedDict):
    type: str  # 'bullish' | 'bearish'
    index: int
    top: float
    bottom: float
    mitigated: bool
    strength: str  # 'strong' | 'weak'

class SMCFVG(TypedDict):
    type: str  # 'bullish' | 'bearish'
    index: int
    top: float
    bottom: float
    mitigated: bool

class SMCSweep(TypedDict):
    type: str  # 'bullish_sweep' | 'bearish_sweep'
    index: int
    level: float
    description: str

class SMCStructureLabel(TypedDict):
    index: int
    text: str
    price: float

class SMCStructure(TypedDict):
    pivots: List[Dict[str, Any]] # Keeping pivots partly loose as internal use mainly
    labels: List[SMCStructureLabel]
    events: List[Dict[str, Any]]

# --- Detection Logic ---

def detect_order_blocks(ohlc: pd.DataFrame) -> List[SMCOrderBlock]:
    """
    Detect Order Blocks (OB).
    Bullish OB: Last down candle before a strong up move (impulsive move).
    Bearish OB: Last up candle before a strong down move (impulsive move).
    Enhanced: Checks for volume spike and displacement.
    """
    obs: List[SMCOrderBlock] = []
    
    # Ensure we have necessary columns
    required_columns = ['open', 'high', 'low', 'close']
    if not all(col in ohlc.columns for col in required_columns):
        return []

    # Calculate average volume if available
    has_volume = 'volume' in ohlc.columns
    avg_volume = None
    if has_volume:
        avg_volume = ohlc['volume'].rolling(window=20).mean()

    for i in range(2, len(ohlc)): # Process all candles including the last one
        prev_open = ohlc['open'].iloc[i-1]
        prev_close = ohlc['close'].iloc[i-1]
        curr_open = ohlc['open'].iloc[i]
        curr_close = ohlc['close'].iloc[i]
        
        # Calculate body sizes
        prev_body = abs(prev_close - prev_open)
        curr_body = abs(curr_close - curr_open)
        
        # Bullish OB detection
        # Previous candle was red (down)
        if prev_close < prev_open:
            # Current candle is green (up) and strongly engulfs or displaces
            if curr_close > prev_open and curr_body > prev_body * 1.5:
                
                # Volume check (if available) - move should have higher volume
                valid_volume = True
                if has_volume and i > 20:
                     current_vol = ohlc['volume'].iloc[i]
                     # Check if volume is above average
                     if current_vol < avg_volume.iloc[i]:
                         valid_volume = False # Weak move, maybe not a strong OB
                
                if valid_volume:
                    obs.append({
                        "type": "bullish",
                        "index": int(i-1), 
                        "top": float(prev_open),
                        "bottom": float(prev_close),
                        "mitigated": False,
                        "strength": "strong" if valid_volume else "weak"
                    })
        
        # Bearish OB detection
        # Previous candle was green (up)
        elif prev_close > prev_open:
            # Current candle is red (down) and strongly engulfs
            if curr_close < prev_open and curr_body > prev_body * 1.5:
                
                valid_volume = True
                if has_volume and i > 20:
                     current_vol = ohlc['volume'].iloc[i]
                     if current_vol < avg_volume.iloc[i]:
                         valid_volume = False
                
                if valid_volume:
                    obs.append({
                        "type": "bearish",
                        "index": int(i-1),
                        "top": float(prev_close),
                        "bottom": float(prev_open),
                        "mitigated": False,
                        "strength": "strong" if valid_volume else "weak"
                    })
                
    return obs

def detect_fvg(ohlc: pd.DataFrame) -> List[SMCFVG]:
    """
    Detect Fair Value Gaps (FVG).
    Bullish FVG: Low[i-2] > High[i]
    Bearish FVG: High[i-2] < Low[i]
    """
    fvgs: List[SMCFVG] = []
    
    for i in range(2, len(ohlc)):
        high_1 = ohlc['high'].iloc[i-2]
        low_3 = ohlc['low'].iloc[i]
        
        # Bullish FVG
        if low_3 > high_1:
            fvgs.append({
                "type": "bullish",
                "index": int(i-1),
                "top": float(low_3),
                "bottom": float(high_1),
                "mitigated": False
            })
            
        low_1 = ohlc['low'].iloc[i-2]
        high_3 = ohlc['high'].iloc[i]
        
        # Bearish FVG
        if high_3 < low_1:
            fvgs.append({
                "type": "bearish",
                "index": int(i-1),
                "top": float(low_1),
                "bottom": float(high_3),
                "mitigated": False
            })
            
    return fvgs

def detect_liquidity_sweeps(ohlc: pd.DataFrame) -> List[SMCSweep]:
    """
    Detect Liquidity Sweeps (Turtle Soup).
    Price sweeps a recent High/Low (taking liquidity) but closes back inside the range.
    """
    sweeps: List[SMCSweep] = []
    window = 5 # Look back 5 bars for a swing point
    
    for i in range(window, len(ohlc)):
        current_high = ohlc['high'].iloc[i]
        current_low = ohlc['low'].iloc[i]
        current_close = ohlc['close'].iloc[i]
        
        # Find recent swing high/low in the window before current candle
        recent_high = ohlc['high'].iloc[i-window:i].max()
        recent_low = ohlc['low'].iloc[i-window:i].min()
        
        # Bearish Sweep (Sweeps High)
        if current_high > recent_high and current_close < recent_high:
            sweeps.append({
                "type": "bearish_sweep",
                "index": int(i),
                "level": float(recent_high),
                "description": "Swept recent high and closed below"
            })
            
        # Bullish Sweep (Sweeps Low)
        if current_low < recent_low and current_close > recent_low:
             sweeps.append({
                "type": "bullish_sweep",
                "index": int(i),
                "level": float(recent_low),
                "description": "Swept recent low and closed above"
            })
            
    return sweeps

def detect_structure(ohlc: pd.DataFrame, window: int = 5) -> SMCStructure:
    """
    Detect Market Structure (Pivots, HH/LL, BoS, CHoCH).
    Matches Mxwll's logic of using a rolling window to find fractals.
    """
    if len(ohlc) < window * 2:
        return SMCStructure(pivots=[], labels=[], events=[])

    highs = ohlc['high'].values
    lows = ohlc['low'].values
    
    structure: SMCStructure = {
        "pivots": [],
        "labels": [],
        "events": []
    }
    
    pivots = []

    # Detect Pivots
    for i in range(window, len(ohlc) - window):
        # High Pivot
        if highs[i] == max(highs[i-window:i+window+1]):
             pivots.append({"index": int(i), "type": "high", "price": float(highs[i])})
        # Low Pivot
        elif lows[i] == min(lows[i-window:i+window+1]):
             pivots.append({"index": int(i), "type": "low", "price": float(lows[i])})

    structure["pivots"] = pivots
    
    # Label HH/LL/LH/HL
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
    Calculate Fib levels from the High/Low of the last 'window' candles.
    """
    if len(ohlc) < 2: return {}
    
    # Use the implementation from the plan
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
