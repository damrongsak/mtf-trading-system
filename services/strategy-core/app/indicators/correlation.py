import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

def calculate_rolling_correlation(series1: pd.Series, series2: pd.Series, window: int = 20) -> pd.Series:
    """
    Calculate the rolling correlation between two price series.
    Useful for detecting breakdown in typical inverse/direct relationships.
    """
    return series1.rolling(window=window).corr(series2)

def detect_smt_divergence(
    symbol1_ohlc: pd.DataFrame, 
    symbol2_ohlc: pd.DataFrame, 
    window: int = 5,
    relationship: str = "inverse"
) -> Dict[str, Any]:
    """
    Detect SMT (Smart Money Technique) divergence between two symbols.
    
    Standard SMT pairs:
    - EUR/USD and GBP/USD (Direct)
    - XAU/USD and DXY (Inverse)
    - BTC/USD and ETH/USD (Direct)
    
    Bullish SMT Divergence (Inverse Relationship, e.g., XAU vs DXY):
    - Symbol 1 (XAU) fails to make a Lower Low (LL) while Symbol 2 (DXY) makes a Higher High (HH).
    
    Bearish SMT Divergence (Inverse Relationship):
    - Symbol 1 (XAU) fails to make a Higher High (HH) while Symbol 2 (DXY) makes a Lower Low (LL).
    """
    if len(symbol1_ohlc) < window + 1 or len(symbol2_ohlc) < window + 1:
        return {"divergence": "NONE", "strength": 0.0}

    # Align indexes to ensure we are comparing the same timestamps
    common_idx = symbol1_ohlc.index.intersection(symbol2_ohlc.index)
    s1 = symbol1_ohlc.loc[common_idx]
    s2 = symbol2_ohlc.loc[common_idx]

    if len(common_idx) < window + 1:
        return {"divergence": "NONE", "strength": 0.0}

    # Recent Highs/Lows
    s1_highs = s1['high'].rolling(window=window).max()
    s1_lows = s1['low'].rolling(window=window).min()
    s2_highs = s2['high'].rolling(window=window).max()
    s2_lows = s2['low'].rolling(window=window).min()

    # Current Extremes
    curr_s1_high = s1['high'].iloc[-1]
    curr_s1_low = s1['low'].iloc[-1]
    curr_s2_high = s2['high'].iloc[-1]
    curr_s2_low = s2['low'].iloc[-1]

    # Previous Extremes (excluding current)
    prev_s1_high = s1['high'].shift(1).rolling(window=window).max().iloc[-1]
    prev_s1_low = s1['low'].shift(1).rolling(window=window).min().iloc[-1]
    prev_s2_high = s2['high'].shift(1).rolling(window=window).max().iloc[-1]
    prev_s2_low = s2['low'].shift(1).rolling(window=window).min().iloc[-1]

    divergence = "NONE"
    strength = 0.0

    if relationship == "inverse":
        # Bullish SMT: One fails to make LL while the other makes HH
        # Case A: S1 (Gold) fails to make LL, S2 (DXY) makes HH
        if curr_s1_low > prev_s1_low and curr_s2_high > prev_s2_high:
            divergence = "BULLISH_SMT"
            strength = abs(curr_s2_high - prev_s2_high) / prev_s2_high
        # Case B: S1 (Gold) makes LL, S2 (DXY) fails to make HH
        elif curr_s1_low < prev_s1_low and curr_s2_high < prev_s2_high:
            divergence = "BULLISH_SMT"
            strength = abs(curr_s1_low - prev_s1_low) / prev_s1_low
        
        # Bearish SMT: One fails to make HH while the other makes LL
        # Case A: S1 (Gold) fails to make HH, S2 (DXY) makes LL
        elif curr_s1_high < prev_s1_high and curr_s2_low < prev_s2_low:
            divergence = "BEARISH_SMT"
            strength = abs(curr_s2_low - prev_s2_low) / prev_s2_low
        # Case B: S1 (Gold) makes HH, S2 (DXY) fails to make LL
        elif curr_s1_high > prev_s1_high and curr_s2_low > prev_s2_low:
            divergence = "BEARISH_SMT"
            strength = abs(curr_s1_high - prev_s1_high) / prev_s1_high

    else: # Direct relationship (e.g., EURUSD vs GBPUSD)
        # Bullish SMT: S1 fails to make LL, S2 makes LL (One sweeps, one doesn't)
        if curr_s1_low > prev_s1_low and curr_s2_low < prev_s2_low:
            divergence = "BULLISH_SMT"
            strength = abs(curr_s2_low - prev_s2_low) / prev_s2_low
        elif curr_s1_low < prev_s1_low and curr_s2_low > prev_s2_low:
            divergence = "BULLISH_SMT"
            strength = abs(curr_s1_low - prev_s1_low) / prev_s1_low

        # Bearish SMT: S1 fails to make HH, S2 makes HH
        elif curr_s1_high < prev_s1_high and curr_s2_high > prev_s2_high:
            divergence = "BEARISH_SMT"
            strength = abs(curr_s2_high - prev_s2_high) / prev_s2_high
        elif curr_s1_high > prev_s1_high and curr_s2_high < prev_s2_high:
            divergence = "BEARISH_SMT"
            strength = abs(curr_s1_high - prev_s1_high) / prev_s1_high

    return {
        "divergence": divergence,
        "strength": float(strength),
        "timestamp": common_idx[-1].isoformat() if hasattr(common_idx[-1], 'isoformat') else str(common_idx[-1]),
        "meta": {
            "s1_high": float(curr_s1_high),
            "s1_low": float(curr_s1_low),
            "s2_high": float(curr_s2_high),
            "s2_low": float(curr_s2_low)
        }
    }
