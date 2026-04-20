import numpy as np
from scipy.stats import norm

def black_scholes_greeks(S, K, T, r, sigma, option_type='CALL'):
    """
    Calculate Black-Scholes Greeks (Vectorized).
    
    Args:
        S: Current price of the underlying
        K: Strike price
        T: Time to expiration (in years)
        r: Risk-free interest rate (e.g. 0.05 for 5%)
        sigma: Implied volatility (e.g. 0.20 for 20%)
        option_type: 'CALL' or 'PUT'
        
    Returns:
        dict: {delta, gamma, vega, theta, vanna, charm}
    """
    # Defensive checks for T=0 to avoid division by zero
    T = np.maximum(T, 1e-10)
    sigma = np.maximum(sigma, 1e-10)
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    # Probability Density Function
    pdf = norm.pdf(d1)
    
    if option_type.upper() == 'CALL':
        delta = norm.cdf(d1)
        theta = -(S * pdf * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)
    else:
        delta = norm.cdf(d1) - 1
        theta = -(S * pdf * sigma) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * norm.cdf(-d2)
        
    gamma = pdf / (S * sigma * np.sqrt(T))
    vega = S * pdf * np.sqrt(T)
    
    # Second Order Greeks
    # Vanna: dDelta / dSigma (How much delta changes as IV changes)
    vanna = -pdf * d2 / sigma
    
    # Charm: dDelta / dT (Delta decay per year)
    # This is rough approximation for spot options
    if option_type.upper() == 'CALL':
        charm = -pdf * ( (r / (sigma * np.sqrt(T))) - (d2 / (2 * T)) )
    else:
        charm = -pdf * ( (r / (sigma * np.sqrt(T))) - (d2 / (2 * T)) )
        
    return {
        "delta": float(delta) if np.isscalar(delta) else delta,
        "gamma": float(gamma) if np.isscalar(gamma) else gamma,
        "vega": float(vega) if np.isscalar(vega) else vega,
        "theta": float(theta) if np.isscalar(theta) else theta,
        "vanna": float(vanna) if np.isscalar(vanna) else vanna,
        "charm": float(charm) if np.isscalar(charm) else charm
    }
