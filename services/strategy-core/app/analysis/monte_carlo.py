import numpy as np
import pandas as pd
from typing import Dict, List, Any

def run_monte_carlo(trades: List[Dict[str, Any]], n_sims: int = 1000) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation on a list of trades to determine robust performance metrics.
    
    Args:
        trades: List of trade objects (must contain 'pnl' or 'return_pct').
        n_sims: Number of simulations to run.
        
    Returns:
        Dictionary with confidence intervals for metrics.
    """
    if not trades:
        return {}
        
    # Extract trade returns
    returns = []
    for t in trades:
        # Prefer percentage return, fallback to absolute PnL relative to something?
        # Let's assume input has 'return_pct' (0.01 = 1%)
        if 'return_pct' in t:
            returns.append(t['return_pct'])
        elif 'pnl' in t and 'entry_price' in t:
             # Rough approximation if pct not pre-calculated
             returns.append(t['pnl'] / (t['entry_price'] * t.get('lot', 0.01) * 100000) if t.get('entry_price') else 0)
    
    if not returns:
        return {}
        
    returns_array = np.array(returns)
    n_trades = len(returns_array)
    
    final_returns = []
    max_drawdowns = []
    
    # Run simulations
    rng = np.random.default_rng()
    
    for _ in range(n_sims):
        # Shuffle returns with replacement (Bootstrap) or without (Permutation)?
        # Usually Bootstrap (with replacement) is used for "what if market conditions recur differently"
        # Permutation (without replacement) is used for "was the ordering lucky?"
        # Let's use Shuffle (without replacement) to test sequence risk primarily (Drawdown robustness)
        
        sim_returns = rng.permutation(returns_array)
        
        # Calculate Equity Curve
        # Start at 1.0
        equity_curve = np.cumprod(1 + sim_returns)
        
        final_return = equity_curve[-1] - 1
        final_returns.append(final_return)
        
        # Calculate Max Drawdown
        running_max = np.maximum.accumulate(np.insert(equity_curve, 0, 1.0))
        # Drawdown = (Current - Peak) / Peak
        # Insert 1.0 at start to represent initial capital
        padded_equity = np.insert(equity_curve, 0, 1.0)
        dd = (padded_equity - running_max) / running_max
        max_dd = np.min(dd)
        max_drawdowns.append(max_dd)
        
    # Calculate Percentiles
    param_95_dd = np.percentile(max_drawdowns, 5) # 5th percentile (negative number, deep drawdown)
    param_95_ret = np.percentile(final_returns, 5) # 5th percentile of returns (worst case)
    
    median_dd = np.median(max_drawdowns)
    median_ret = np.median(final_returns)
    
    return {
        "iterations": n_sims,
        "max_drawdown": {
            "p95": float(param_95_dd),
            "median": float(median_dd),
            "worst": float(np.min(max_drawdowns))
        },
        "total_return": {
            "p95": float(param_95_ret),
            "median": float(median_ret),
            "best": float(np.max(final_returns))
        }
    }
