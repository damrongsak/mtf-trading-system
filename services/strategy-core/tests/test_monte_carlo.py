
import pytest
import numpy as np
from app.analysis.monte_carlo import run_monte_carlo

def test_monte_carlo_logic():
    # Mock trades: 50% win rate, win=+10%, loss=-5%
    trades = []
    for i in range(50):
        trades.append({'return_pct': 0.10})
        trades.append({'return_pct': -0.05})
    
    # Run simulation
    results = run_monte_carlo(trades, n_sims=100)
    
    assert results['iterations'] == 100
    assert 'max_drawdown' in results
    assert 'total_return' in results
    
    # With positive expectancy, median return should be positive
    # (1.1 * 0.95)^50 = (1.045)^50 > 1
    assert results['total_return']['median'] > 0
    
    # p95 drawdown should be negative
    assert results['max_drawdown']['p95'] < 0

def test_monte_carlo_empty():
    results = run_monte_carlo([], n_sims=10)
    assert results == {}
