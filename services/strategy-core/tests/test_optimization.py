import pytest
import pandas as pd
import numpy as np
from app.analysis.optimization import run_grid_search

def test_run_grid_search_empty():
    df = pd.DataFrame()
    results = run_grid_search(df, {})
    assert results == []

def test_run_grid_search_basic():
    # Create simple mock data: uptrend where crossovers happen
    prices = [10, 11, 12, 13, 14, 13, 12, 11, 10, 9, 8, 9, 10, 11, 12]
    # Expand to be enough for MA calculation
    prices = prices * 10 
    
    df = pd.DataFrame({
        "close": prices,
        "open": prices, 
        "high": prices,
        "low": prices,
        "volume": [1000] * len(prices)
    })
    df.index = pd.date_range("2024-01-01", periods=len(prices), freq="1h")
    
    # Param grid
    grid = {
        "fast_window": [2, 5],
        "slow_window": [10, 20]
    }
    
    results = run_grid_search(df, grid, capital=10000)
    
    assert len(results) > 0
    assert "params" in results[0]
    assert "metrics" in results[0]
    
    # Check if params are within grid
    fast = results[0]["params"]["fast_window"]
    assert fast in [2, 5]
    
    # Check sorting (Sharpe)
    sharpes = [r["metrics"]["sharpe_ratio"] for r in results]
    assert sharpes == sorted(sharpes, reverse=True)
