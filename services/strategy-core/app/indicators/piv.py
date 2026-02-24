import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from typing import Dict, List, Tuple, Optional
from app.indicators.volatility import calculate_atr

def calculate_n_bands(df: pd.DataFrame, gvz: float = 20.0, multiplier: float = 2.0, multipliers: Optional[List[float]] = None) -> Dict[str, List[float]]:
    """
    Calculate Dynamic N Bands based on ATR and Gold Volatility (GVZ).
    GVZ is expected as a raw percentage (e.g., 20.0).
    """
    close = df['close']
    atr = calculate_atr(df['high'], df['low'], df['close'])
    
    # Normalize GVZ (e.g., 20.0 -> 0.20)
    gvz_norm = gvz / 100.0
    
    if multipliers is None:
        multipliers = [1.0, 2.0, 3.0]
        if multiplier not in multipliers:
            multipliers.append(multiplier)
    
    bands = {}
    for m in multipliers:
        # Volatility Buffer = multiplier * ATR * (1 + GVZ_impact)
        # Higher GVZ expands the bands
        buffer = m * atr * (1 + gvz_norm)
        bands[f"n_band_upper_{m}"] = (close + buffer).iloc[-1]
        bands[f"n_band_lower_{m}"] = (close - buffer).iloc[-1]
        
    return bands

def calculate_piv_levels(df: pd.DataFrame, gvz: float = 20.0, prominence: float = 0.5) -> List[float]:
    """
    Volatility-Based Support/Resistance (VBSR) via peak detection.
    Identifies levels where the volatility-adjusted price reaches extreme values.
    """
    close = df['close']
    atr = calculate_atr(df['high'], df['low'], df['close'])
    
    # Combine Price and Volatility into a single 'Power' series
    # Higher price + Higher volatility = extreme level
    vol_price = close * (1 + (atr / close) * (gvz / 100.0))
    
    # Peak Detection
    peaks, _ = find_peaks(vol_price, prominence=prominence)
    troughs, _ = find_peaks(-vol_price, prominence=prominence)
    
    levels = []
    for p in peaks:
        levels.append(float(close.iloc[p]))
    for t in troughs:
        levels.append(float(close.iloc[t]))
        
    # Return unique, sorted levels
    return sorted(list(set(levels)))

def calculate_true_slope(series: pd.Series, window: int = 5) -> pd.Series:
    """
    Angle-based slope detection.
    Normalizes time and price units to return an angle in degrees (-90 to 90).
    """
    # Price difference
    dy = series.diff(1)
    
    # We treat time-step as 1 unit. 
    # To get a meaningful angle, we must scale dy by the series' volatility.
    vol = dy.rolling(window=20).std().ffill()
    
    # Scale dy by volatility to make it 'unitless'
    # dy / vol represents how many standard deviations price moved per step
    scaled_dy = dy / (vol + 1e-9)
    
    # atan (scaled_dy / 1) -> angle in radians
    angle_rad = np.arctan(scaled_dy)
    
    # Convert to Degrees
    angle_deg = np.degrees(angle_rad)
    
    return angle_deg.rolling(window=window).mean()

def calculate_volatility_confluence(bands: Dict[str, pd.Series], piv_levels: List[float], current_price: float) -> Optional[float]:
    """
    Check for confluence between N Bands and VBSR levels near current price.
    Returns a score 0-1 based on proximity.
    """
    # Implementation of confluence logic...
    pass
