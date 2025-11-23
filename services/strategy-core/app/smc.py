import pandas as pd
import numpy as np
from typing import List, Dict, Any

def detect_order_blocks(ohlc: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Detect Order Blocks (OB).
    Bullish OB: Last down candle before a strong up move.
    Bearish OB: Last up candle before a strong down move.
    """
    obs = []
    
    # Ensure we have necessary columns
    required_columns = ['open', 'high', 'low', 'close']
    if not all(col in ohlc.columns for col in required_columns):
        return []

    # Simple logic: Look for engulfing patterns or strong moves
    # This is a simplified version for MVP
    for i in range(2, len(ohlc)):
        prev_open = ohlc['open'].iloc[i-1]
        prev_close = ohlc['close'].iloc[i-1]
        curr_open = ohlc['open'].iloc[i]
        curr_close = ohlc['close'].iloc[i]
        
        # Bullish OB detection
        # Previous candle was red (down)
        if prev_close < prev_open:
            # Current candle is green (up) and engulfs previous body
            if curr_close > prev_open and curr_open <= prev_close:
                obs.append({
                    "type": "bullish",
                    "index": int(i-1), # Index of the OB candle
                    "top": float(prev_open),
                    "bottom": float(prev_close),
                    "mitigated": False
                })
        
        # Bearish OB detection
        # Previous candle was green (up)
        elif prev_close > prev_open:
            # Current candle is red (down) and engulfs previous body
            if curr_close <= prev_open and curr_open >= prev_close:
                obs.append({
                    "type": "bearish",
                    "index": int(i-1),
                    "top": float(prev_close),
                    "bottom": float(prev_open),
                    "mitigated": False
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
        # Bullish FVG
        # Candle i-2 high, Candle i low
        # Wait, definition:
        # Bullish FVG: The gap between the High of the first candle (i-2) and the Low of the third candle (i)
        # Wait, standard definition:
        # Bullish FVG: Created when price moves up strongly. Gap is between High of candle 1 and Low of candle 3.
        # So Low[3] > High[1].
        
        high_1 = ohlc['high'].iloc[i-2]
        low_3 = ohlc['low'].iloc[i]
        
        if low_3 > high_1:
            fvgs.append({
                "type": "bullish",
                "index": int(i-1), # The FVG is essentially the middle candle's range
                "top": float(low_3),
                "bottom": float(high_1),
                "mitigated": False
            })
            
        # Bearish FVG
        # Created when price moves down strongly. Gap is between Low of candle 1 and High of candle 3.
        # So High[3] < Low[1].
        
        low_1 = ohlc['low'].iloc[i-2]
        high_3 = ohlc['high'].iloc[i]
        
        if high_3 < low_1:
            fvgs.append({
                "type": "bearish",
                "index": int(i-1),
                "top": float(low_1),
                "bottom": float(high_3),
                "mitigated": False
            })
            
    return fvgs
