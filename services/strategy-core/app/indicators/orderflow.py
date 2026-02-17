
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

from numba import njit
import numpy as np

@njit(cache=True)
def detect_imbalance_nb(levels_array, ratio=3.0, min_vol=10.0):
    """
    Numba-accelerated diagonal imbalance detection.
    levels_array: [N, 3] where cols are [price, bid_vol, ask_vol]
    """
    n = len(levels_array)
    if n < 2:
        return np.zeros(0), np.zeros(0)
        
    buying_imbalances = []
    selling_imbalances = []
    
    # 1. Buying Imbalance: Ask[i+1] vs Bid[i]
    for i in range(n - 1):
        bid_vol = levels_array[i, 1]
        ask_vol = levels_array[i+1, 2]
        
        if ask_vol > min_vol and (bid_vol == 0 or (ask_vol / bid_vol >= ratio)):
            buying_imbalances.append(levels_array[i+1, 0])
            
    # 2. Selling Imbalance: Bid[i+1] vs Ask[i]
    for i in range(n - 1):
        ask_vol = levels_array[i, 2]
        bid_vol = levels_array[i+1, 1]
        
        if bid_vol > min_vol and (ask_vol == 0 or (bid_vol / ask_vol >= ratio)):
            selling_imbalances.append(levels_array[i+1, 0])
            
    return np.array(buying_imbalances), np.array(selling_imbalances)

def detect_imbalance(candle: Dict[str, Any], ratio: float = 3.0, min_vol: float = 10) -> Dict[str, List[float]]:
    """
    Identify price levels with aggressive Buying/Selling Diagonal Imbalance.
    Wraps the Numba-accelerated core.
    """
    footprint = candle.get('footprint')
    if not footprint or not isinstance(footprint, list):
        return {'buying': [], 'selling': []}
        
    # Prepare array for Numba: [price, bid_vol, ask_vol]
    try:
        data = []
        for f in footprint:
            data.append([float(f['price']), float(f.get('bid_vol', 0)), float(f.get('ask_vol', 0))])
        
        # Sort by price
        data.sort(key=lambda x: x[0])
        levels_array = np.array(data)
        
        buying, selling = detect_imbalance_nb(levels_array, ratio, min_vol)
        
        return {
            'buying': buying.tolist(),
            'selling': selling.tolist()
        }
    except Exception:
        return {'buying': [], 'selling': []}

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
