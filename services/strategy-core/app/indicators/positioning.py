import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

def detect_crowding(
    call_oi: List[float], 
    put_oi: List[float], 
    strikes: List[float], 
    current_price: float
) -> Dict[str, Any]:
    """
    Analyze positioning crowding from Open Interest data.
    
    Args:
        call_oi: List of call open interest values
        put_oi: List of put open interest values
        strikes: List of strike prices
        current_price: Current underlying price
        
    Returns:
        Dictionary containing:
        - put_call_ratio: PCR at current price level
        - crowding_regime: "Long Crowded" | "Short Crowded" | "Balanced"
        - max_pain_strike: Strike with maximum total OI
        - skew: OTM Put OI / OTM Call OI ratio
        - total_call_oi: Sum of all call OI
        - total_put_oi: Sum of all put OI
    """
    if not call_oi or not put_oi or not strikes:
        return {"error": "Insufficient OI data"}
    
    if len(call_oi) != len(put_oi) or len(call_oi) != len(strikes):
        return {"error": "Mismatched data lengths"}
    
    # Convert to numpy arrays for easier manipulation
    call_oi_arr = np.array(call_oi)
    put_oi_arr = np.array(put_oi)
    strikes_arr = np.array(strikes)
    
    # 1. Calculate Total OI
    total_call_oi = float(np.sum(call_oi_arr))
    total_put_oi = float(np.sum(put_oi_arr))
    
    # 2. Put/Call Ratio (overall)
    pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0.0
    
    # 3. Max Pain Strike (strike with maximum total OI)
    total_oi_per_strike = call_oi_arr + put_oi_arr
    max_pain_idx = np.argmax(total_oi_per_strike)
    max_pain_strike = float(strikes_arr[max_pain_idx])
    
    # 4. OI Skew (OTM Put / OTM Call ratio)
    # OTM Calls: strikes > current_price
    # OTM Puts: strikes < current_price
    otm_call_mask = strikes_arr > current_price
    otm_put_mask = strikes_arr < current_price
    
    otm_call_oi = float(np.sum(call_oi_arr[otm_call_mask]))
    otm_put_oi = float(np.sum(put_oi_arr[otm_put_mask]))
    
    skew = otm_put_oi / otm_call_oi if otm_call_oi > 0 else 0.0
    
    # 5. Crowding Regime Classification
    # PCR > 1.5: Short Crowded (more puts = bearish positioning)
    # PCR < 0.7: Long Crowded (more calls = bullish positioning)
    # Otherwise: Balanced
    if pcr > 1.5:
        crowding_regime = "Short Crowded"
    elif pcr < 0.7:
        crowding_regime = "Long Crowded"
    else:
        crowding_regime = "Balanced"
    
    return {
        "put_call_ratio": round(pcr, 4),
        "crowding_regime": crowding_regime,
        "max_pain_strike": round(max_pain_strike, 2),
        "skew": round(skew, 4),
        "total_call_oi": round(total_call_oi, 2),
        "total_put_oi": round(total_put_oi, 2),
        "otm_call_oi": round(otm_call_oi, 2),
        "otm_put_oi": round(otm_put_oi, 2)
    }


def calculate_max_pain(
    call_oi: List[float],
    put_oi: List[float],
    strikes: List[float]
) -> Dict[str, Any]:
    """
    Calculate Max Pain price level where option sellers experience minimum loss.
    
    Max Pain is the strike price where the total value of options (calls + puts)
    expiring worthless is maximized, causing maximum pain to option buyers.
    
    Args:
        call_oi: List of call open interest values
        put_oi: List of put open interest values
        strikes: List of strike prices
        
    Returns:
        Dictionary containing:
        - max_pain_strike: Strike with maximum pain
        - total_pain_at_max: Total intrinsic value at max pain strike
    """
    if not call_oi or not put_oi or not strikes:
        return {"error": "Insufficient data"}
    
    call_oi_arr = np.array(call_oi)
    put_oi_arr = np.array(put_oi)
    strikes_arr = np.array(strikes)
    
    # Calculate pain at each potential price point
    pain_values = []
    
    for test_price in strikes_arr:
        # Calculate intrinsic value for calls (max(0, test_price - strike))
        call_value = np.sum(call_oi_arr * np.maximum(0, test_price - strikes_arr))
        
        # Calculate intrinsic value for puts (max(0, strike - test_price))
        put_value = np.sum(put_oi_arr * np.maximum(0, strikes_arr - test_price))
        
        # Total pain is the sum of all intrinsic values
        total_pain = call_value + put_value
        pain_values.append(total_pain)
    
    # Max pain is where total intrinsic value is MINIMUM
    min_pain_idx = np.argmin(pain_values)
    max_pain_strike = float(strikes_arr[min_pain_idx])
    total_pain_at_max = float(pain_values[min_pain_idx])
    
    return {
        "max_pain_strike": round(max_pain_strike, 2),
        "total_pain_at_max": round(total_pain_at_max, 2)
    }
