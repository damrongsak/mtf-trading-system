import pytest
import numpy as np
from app.utils.options_math import black_scholes_greeks

def test_vectorized_greeks_calls():
    # S=2400, K=2400, T=0.25 (90 days), r=0.045, sigma=0.15
    greeks = black_scholes_greeks(S=2400, K=2400, T=0.25, r=0.045, sigma=0.15, option_type='CALL')
    
    assert greeks['delta'] > 0.5 # ATM Call Delta ~ 0.5
    assert greeks['gamma'] > 0
    assert greeks['vega'] > 0
    assert greeks['vanna'] is not None
    assert greeks['charm'] is not None
    
    print(f"ATM CALL Greeks: {greeks}")

def test_vanna_charm_sensitivity():
    # Vanna: Delta sensitivity to Vol
    # Charm: Delta sensitivity to Time
    S = 2400
    K = 2450
    T = 0.1
    sigma = 0.2
    
    g1 = black_scholes_greeks(S=S, K=K, T=T, r=0.05, sigma=sigma, option_type='CALL')
    g2 = black_scholes_greeks(S=S, K=K, T=T, r=0.05, sigma=sigma + 0.01, option_type='CALL')
    
    # Delta should change if Vanna is non-zero
    delta_diff = g2['delta'] - g1['delta']
    vanna_pred = g1['vanna'] * 0.01
    
    # High precision match not required for proxy logic, but should be directional
    assert np.sign(delta_diff) == np.sign(vanna_pred)
    print(f"Vanna Delta Prediction OK: {delta_diff:.6f} vs {vanna_pred:.6f}")

def test_puts_greeks():
    greeks = black_scholes_greeks(S=2400, K=2400, T=0.25, r=0.045, sigma=0.15, option_type='PUT')
    assert greeks['delta'] < -0.4
    assert greeks['gamma'] > 0
    print(f"ATM PUT Greeks: {greeks}")
