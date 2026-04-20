import pandas as pd
import yfinance as yf
import numpy as np
from typing import Union, List

def get_gvz_index() -> float:
    """
    Fetch the latest GVZ (Cboe Gold Volatility Index) from Yahoo Finance.
    Falls back to a default value (15.0) if fetch fails.
    """
    try:
        gvz = yf.Ticker("^GVZ")
        hist = gvz.history(period="1d")
        if not hist.empty:
            # Returns value in percentage (e.g. 15.2)
            return float(hist['Close'].iloc[-1]) / 100.0
    except Exception:
        pass
    return 0.15  # 15% default ATM Vol

def get_synthetic_iv(spot: float, strikes: Union[float, List[float], np.ndarray], atm_iv: float) -> Union[float, np.ndarray]:
    """
    Calculate strike-specific Implied Volatility using a quadratic skew/smile model.
    Tailored for Gold's characteristic Call-Skew.
    
    Formula: IV = ATM + a*(K/S - 1) + b*(K/S - 1)^2
    """
    # XAUUSD specific coefficients (Approximated institutional skew)
    # a > 0 implies Call-Skew (OTM Calls more expensive)
    # b > 0 implies Smile (OTM both sides more expensive)
    a = 0.08  # Skew
    b = 0.15  # Convexity/Smile
    
    strikes = np.array(strikes) if isinstance(strikes, (list, np.ndarray)) else strikes
    
    # Moneyness (relative to spot)
    m = (strikes / spot) - 1.0
    
    iv = atm_iv + a * m + b * (m**2)
    
    # Floor at 5% to avoid negative/unrealistic IV
    return np.maximum(iv, 0.05)

def get_vanna_charm_sensitivity(fragility_index: float) -> str:
    """
    Map LFI to a human-readable alert.
    """
    if fragility_index > 80:
        return "CRITICAL: Liquidity Wall Breach Imminent (High Charm Decay)"
    elif fragility_index > 60:
        return "WARNING: Fragile Wall (Vanna Sensitivity Detected)"
    return "STABLE: Institutional Support Intact"
