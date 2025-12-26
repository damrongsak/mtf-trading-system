
import pandas as pd
import numpy as np
import sys
# Make sure app is in path
sys.path.append('/app')

from app.analysis.optimization import run_grid_search

def verify():
    print("Starting verification...")
    # Mock Data
    dates = pd.date_range("2023-01-01", periods=100, freq="15min")
    close = np.linspace(100, 200, 100)
    data = pd.DataFrame({"close": close}, index=dates)

    # Custom Code that uses 'params'
    code = """
import vectorbt as vbt

def strategy(data, params={}):
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
    print("Running grid search...")
    results = run_grid_search(data, param_grid, code=code)

    if len(results) != 2:
        print(f"FAILED: Expected 2 results, got {len(results)}")
        sys.exit(1)
    
    p1 = results[0]['params']['threshold']
    p2 = results[1]['params']['threshold']
    
    if {p1, p2} != {120, 180}:
        print(f"FAILED: Params mismatch: {p1}, {p2}")
        sys.exit(1)
        
    print("SUCCESS: Optimization verification passed.")

if __name__ == "__main__":
    verify()
