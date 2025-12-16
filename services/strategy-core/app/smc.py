import pandas as pd
import numpy as np
from typing import List, Dict, Any

def detect_order_blocks(ohlc: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Detect Order Blocks (OB).
    Bullish OB: Last down candle before a strong up move (impulsive move).
    Bearish OB: Last up candle before a strong down move (impulsive move).
    Enhanced: Checks for volume spike and displacement.
    """
    obs = []
    
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

def detect_fvg(ohlc: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Detect Fair Value Gaps (FVG).
    Bullish FVG: Low[i-2] > High[i]
    Bearish FVG: High[i-2] < Low[i]
    """
    fvgs = []
    
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

def detect_liquidity_sweeps(ohlc: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Detect Liquidity Sweeps (Turtle Soup).
    Price sweeps a recent High/Low (taking liquidity) but closes back inside the range.
    """
    sweeps = []
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
