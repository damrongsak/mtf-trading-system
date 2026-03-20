import pandas as pd
import numpy as np
from app.analysis.monte_carlo import run_monte_carlo
from app.analysis.optimizer import PortfolioOptimizer
from app.quant.minimax import minimax_engine

def verify_world_class():
    print("--- Verifying World-Class Upgrades ---")
    
    # 1. Verify Monte Carlo Bootstrap
    print("\n1. Testing Monte Carlo Bootstrap...")
    trades = [{'pnl_percent': 1.5}, {'pnl_percent': -0.5}, {'pnl_percent': 2.0}, {'pnl_percent': -1.2}] * 10
    mc_results = run_monte_carlo(trades, n_sims=100, mode="bootstrap")
    print(f"   MC Ruin Probability: {mc_results['ruin_probability']:.4f}")
    print(f"   MC Confidence Bands: {len(mc_results['confidence_bands']['upper_95'])} points")
    
    # 2. Verify Portfolio Optimizer (HRP)
    print("\n2. Testing Portfolio Optimizer (HRP)...")
    data = {
        'Strat_A': pd.Series(np.random.normal(0.001, 0.02, 100)).cumsum(),
        'Strat_B': pd.Series(np.random.normal(0.0008, 0.015, 100)).cumsum()
    }
    weights = PortfolioOptimizer.optimize_multi_strategy(data, method="HRP")
    print(f"   HRP Weights: {weights}")
    
    # 3. Verify Minimax Regret
    print("\n3. Testing Minimax Regret Filter...")
    signal = {
        "entry_price": 2650.0,
        "take_profit": 2670.0,
        "stop_loss": 2645.0,
        "metadata": {"volatility": 0.005}
    }
    passed = minimax_engine.filter_signal(signal, threshold=1.0)
    print(f"   Signal Regret Score: {signal['metadata']['minimax_regret_score']:.2f}")
    print(f"   Signal Passed Filter: {passed}")

if __name__ == "__main__":
    verify_world_class()
