import pandas as pd
import numpy as np
import sys
import os

# Ensure app is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.analysis.optimizer import PortfolioOptimizer

def demo_optimization():
    print("--- PyPortfolioOpt Demonstration ---")
    
    # 1. Create Mock Data (3 Assets, 100 days)
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=100)
    
    # Correlated assets
    asset1 = np.random.normal(0.001, 0.02, 100).cumsum() # Asset A
    asset2 = np.random.normal(0.001, 0.015, 100).cumsum() # Asset B (Lower vol)
    asset3 = np.random.normal(0.0005, 0.03, 100).cumsum() # Asset C (High vol)
    
    df = pd.DataFrame({
        'Asset_A': 100 + asset1,
        'Asset_B': 100 + asset2,
        'Asset_C': 100 + asset3
    }, index=dates)
    
    print(f"Data Shape: {df.shape}")
    print(df.tail())
    print("\n--- Running Optimizer ---")

    # 2. Initialize Optimizer
    opt = PortfolioOptimizer(df)
    
    # 3. Max Sharpe
    print("\n[1] Max Sharpe Ratio:")
    try:
        weights_sharpe = opt.optimize_max_sharpe()
        print(weights_sharpe)
    except Exception as e:
        print(f"Error: {e}")

    # 4. Min Volatility (Risk Parity-like)
    print("\n[2] Min Volatility:")
    try:
        weights_vol = opt.optimize_min_volatility()
        print(weights_vol)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    demo_optimization()
