
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any

def calculate_delta(candle: Dict[str, Any]) -> float:
    """
    Calculate Net Delta (Buy Vol - Sell Vol) from a candle.
    Prioritizes 'footprint' data if available, falls back to 'delta' field.
    """
    # 1. Try calculation from Footprint
    if candle.get('footprint'):
        footprint = candle['footprint']
        # Assumption: footprint has 'bid_vol' and 'ask_vol' per level
        # OR it might be a list of levels. Let's assume list of dicts for now as per plan
        # Structure: [{'price': 100, 'bid_vol': 10, 'ask_vol': 50}, ...]
        if isinstance(footprint, list):
            total_bid = sum(level.get('bid_vol', 0) for level in footprint)
            total_ask = sum(level.get('ask_vol', 0) for level in footprint)
            return float(total_ask - total_bid)
    
    # 2. Fallback to pre-calculated field
    return float(candle.get('delta', 0.0))

def detect_imbalance(candle: Dict[str, Any], ratio: float = 3.0) -> List[float]:
    """
    Identify price levels with aggressive Buying/Selling Imbalance.
    Returns list of price levels where Imbalance detected.
    """
    imbalance_levels = []
    footprint = candle.get('footprint')
    
    if not footprint or not isinstance(footprint, list):
        return []
        
    # Sort by price ascending
    # Logic: Diagonal comparison is standard for Footprint, but for simple MVP
    # we can do horizontal imbalance or just Check for large Ask vs Bid at same level
    # Standard Imbalance is often Ask[i] vs Bid[i+1] (Diagonal). 
    # Let's Implement 'Aggressive Side' dominance at a level for simplicity first.
    
    for level in footprint:
        bid_vol = float(level.get('bid_vol', 0))
        ask_vol = float(level.get('ask_vol', 0))
        
        # Avoid division by zero
        # If bid_vol is 0, any ask_vol > 0 is technically infinite imbalance.
        # We assume if ask_vol > 0 and bid_vol == 0, it is an imbalance.
        if (bid_vol > 0 and (ask_vol / bid_vol >= ratio)) or (bid_vol == 0 and ask_vol > 0):
            imbalance_levels.append(level['price'])
        elif ask_vol > 0 and (bid_vol / ask_vol >= ratio):
            # Selling imbalance (not used for this Buy-Only strategy but good to have)
             pass 
             
    return imbalance_levels

def is_absorption(candle: Dict[str, Any], avg_vol: float) -> bool:
    """
    Detect absorption: High Volume but small price change (Body).
    """
    vol = float(candle.get('volume', 0))
    open_p = float(candle.get('open', 0))
    close_p = float(candle.get('close', 0))
    high_p = float(candle.get('high', 0))
    low_p = float(candle.get('low', 0))
    
    range_total = high_p - low_p
    body_size = abs(close_p - open_p)
    
    if range_total == 0: return False
    
    # Logic: Volume > 1.5x Avg AND Body < 30% of Range
    high_vol_node = vol > (avg_vol * 1.5)
    doji_like = (body_size / range_total) < 0.3
    
    return high_vol_node and doji_like
