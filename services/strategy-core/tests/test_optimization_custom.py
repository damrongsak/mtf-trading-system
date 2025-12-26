
import pytest
import pandas as pd
import numpy as np
from app.analysis.optimization import run_grid_search

def test_run_grid_search_custom_code():
    # Mock Data
    dates = pd.date_range("2023-01-01", periods=100, freq="15min")
    close = np.linspace(100, 200, 100)
    data = pd.DataFrame({"close": close}, index=dates)

    # Custom Code that uses 'params'
    code = """
import vectorbt as vbt

def strategy(data, params={}):
    # Simple logic: Buy if close > threshold defined in params
    threshold = params.get('threshold', 150)
    
    entries = data['close'] > threshold
    exits = data['close'] < threshold
    return entries, exits
"""

    # Param Grid
    param_grid = {
        "threshold": [120, 180] 
    }

    # Run
    results = run_grid_search(data, param_grid, code=code)

    assert len(results) == 2
    
    # Check if params were correctly injected
    p1 = results[0]['params']['threshold']
    p2 = results[1]['params']['threshold']
    assert set([p1, p2]) == {120, 180}
    
    # Metrics should exist
    assert 'total_return' in results[0]['metrics']
    assert 'sharpe_ratio' in results[0]['metrics']

def test_run_grid_search_custom_code_compatibility():
    # Test code that DOESNT accept params (should not crash)
    dates = pd.date_range("2023-01-01", periods=100, freq="15min")
    close = np.linspace(100, 200, 100)
    data = pd.DataFrame({"close": close}, index=dates)

    code = """
import vectorbt as vbt

def strategy(data):
    entries = data['close'] > 150
    exits = data['close'] < 150
    return entries, exits
"""
    param_grid = {"unused": [1, 2]}
    
    results = run_grid_search(data, param_grid, code=code)
    assert len(results) == 2
    # Should work but produce identical results
    assert results[0]['metrics']['total_return'] == results[1]['metrics']['total_return']
