import math
import numpy as np
from scipy.stats import norm
from typing import Optional

def calculate_black_scholes_gamma(
    S: float, 
    K: float, 
    T: float, 
    r: float, 
    sigma: float, 
    q: float = 0.0
) -> float:
    """
    Calculates Gamma for an option using the Black-Scholes model.
    T: Time to expiration in years (DTE / 365.25)
    r: Risk-free rate (e.g. 0.05 for 5%)
    sigma: Implied Volatility (e.g. 0.16 for 16%)
    q: Dividend yield / carry cost (0 for Gold usually)
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
        
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    gamma = (math.exp(-q * T) * norm.pdf(d1)) / (S * sigma * math.sqrt(T))
    return gamma

def calculate_gex_per_strike(
    S: float,
    K: float,
    T: float,
    call_oi: float,
    put_oi: float,
    r: float = 0.05,
    sigma: float = 0.16,
    multiplier: int = 100
) -> float:
    """
    Calculates the Net GEX for a specific strike.
    Standard convention: 
    Call GEX = OI * Gamma * Multiplier * S
    Put GEX = - (OI * Gamma * Multiplier * S)
    """
    gamma = calculate_black_scholes_gamma(S, K, T, r, sigma)
    
    # Notional GEX (Value change in underlying per point moved)
    # Some systems use Strike price for notional, but Spot (S) is more common for GEX.
    call_gex = call_oi * gamma * multiplier * S
    put_gex = put_oi * gamma * multiplier * S * -1
    
    return call_gex + put_gex
