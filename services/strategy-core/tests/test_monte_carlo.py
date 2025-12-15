import pytest
import numpy as np
from app.analysis.monte_carlo import run_monte_carlo

def test_run_monte_carlo_empty():
    res = run_monte_carlo([], 100)
    assert res == {}

def test_run_monte_carlo_basic():
    # Mock trades with returns
    trades = [
        {'return_pct': 0.05},
        {'return_pct': -0.02},
        {'return_pct': 0.03},
        {'return_pct': -0.01},
        {'return_pct': 0.10}
    ]
    
    res = run_monte_carlo(trades, n_sims=50)
    
    assert res["iterations"] == 50
    assert "max_drawdown" in res
    assert "total_return" in res
    
    # Check logic: Median return should be vaguely consistent with sum/product of returns
    # But shuffling preserves the set, so Final Return should be Identical for all simulations?
    # Wait, Monte Carlo Resampling (Bootstrap) uses Replacement.
    # My implementation used Permutation (No Replacement).
    # If using Permutation (shuffling order), Final Return is ALWAYS the same (product of factors is commutative).
    # Only Drawdown changes.
    # If I want to test Return distribution, I MUST use Bootstrap (Random Choice with Replacement).
    
    # Let's verify what I implemented in monte_carlo.py.
    # I used `rng.permutation(returns_array)`. This is without replacement.
    # So `final_return` will be identical for all runs (floating point errors aside).
    # The `total_return` confidence interval will be flat.
    # This is fine for Sequence Risk analysis (Drawdown), but useless for Return analysis.
    # I should switch to Bootstrap in the implementation if I want Return variance.
    # Update: The PRD asked for "Stress-test strategies using randomized trade sequences". Permutation does this.
    # "curve fitting analysis" usually implies Bootstrap.
    # Let's stick to Permutation for now as it tests "what if the order was different".
    
    assert "p95" in res["max_drawdown"]
