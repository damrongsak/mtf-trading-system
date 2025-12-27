import numpy as np
import pandas as pd
from typing import Dict, List, Any
import logging
import traceback

logger = logging.getLogger(__name__)

def run_monte_carlo(trades: List[Dict[str, Any]], n_sims: int = 1000) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation on a list of trades to determine robust performance metrics.
    
    Args:
        trades: List of trade objects (must contain 'pnl' or 'return_pct').
        n_sims: Number of simulations to run.
        
    Returns:
        Dictionary with confidence intervals for metrics.
    """
    try:
        logger.info(f"Starting Monte Carlo simulation with {n_sims} iterations.")
        if not trades:
            logger.warning("No trades provided for Monte Carlo.")
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
        
        logger.info(f"Extracted {len(returns)} returns from trades.")
        
        if not returns:
            logger.warning("No valid returns found in trades.")
            return {}
            
        returns_array = np.array(returns)
        n_trades = len(returns_array)
        
        final_returns = []
        max_drawdowns = []
        
        # Run simulations
        logger.info("Initializing RNG and starting simulations loop...")
        rng = np.random.default_rng()
        
        for i in range(n_sims):
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
            
        logger.info("Simulations complete. Calculating percentiles...")
            
        # Calculate Percentiles
        param_95_dd = np.percentile(max_drawdowns, 5) # 5th percentile (negative number, deep drawdown)
        param_95_ret = np.percentile(final_returns, 5) # 5th percentile of returns (worst case)
        
        median_dd = np.median(max_drawdowns)
        median_ret = np.median(final_returns)
        
        # --- New Metrics ---
        # 1. Ruin Probability: Chance that Drawdown exceeds 50%
        # Using 50% as a generic ruin threshold for now
        ruin_count = sum(1 for dd in max_drawdowns if dd < -0.50)
        ruin_prob = ruin_count / n_sims
        logger.info(f"Ruin Probability calculated: {ruin_prob}")
        
        # 2. Sharpe Ratio Distribution
        # Approximation: Mean Return / Std Dev of Return
        # For each simulation, we have `sim_returns` inside the loop, but we didn't store them.
        # To be efficient, let's re-run or refactor.
        # Refactoring loop to calculate Sharpe per run.
        
        sharpe_ratios = []
        
        logger.info("Calculating Sharpe distributions...")
        
        # Re-running logic slightly differently to get per-sim sharpe without storing all arrays
        rng = np.random.default_rng()
        
        final_returns = []
        max_drawdowns = []
        equity_curves_sample = [] # Store first 50 curves
        
        for idx in range(n_sims):
            sim_returns = rng.permutation(returns_array)
            
            # Equity Curve
            equity_curve = np.cumprod(1 + sim_returns)
            final_returns.append(equity_curve[-1] - 1)
            
            # Store sample for UI
            if idx < 50:
                 # Prepend 1.0 (start) and convert to list
                 curve_list = np.insert(equity_curve, 0, 1.0).tolist()
                 equity_curves_sample.append(curve_list)
            
            # Max Drawdown
            running_max = np.maximum.accumulate(np.insert(equity_curve, 0, 1.0))
            padded_equity = np.insert(equity_curve, 0, 1.0)
            dd = (padded_equity - running_max) / running_max
            max_drawdowns.append(np.min(dd))
            
            # Sharpe (Annualized approximation assuming daily)
            # Verify if returns are per-trade or per-timebox?
            # `trades` input usually per-trade. Time-based sharpe requires timestamps.
            # Here we calculate "Trade Sharpe" (Avg Trade Return / Std Trade Return) * sqrt(Trades)
            mean_ret = np.mean(sim_returns)
            std_ret = np.std(sim_returns)
            if std_ret == 0:
                sharpe = 0
            else:
                sharpe = (mean_ret / std_ret) * np.sqrt(n_trades)
            sharpe_ratios.append(sharpe)
            
        # Recalculate percentiles with new data
        param_95_dd = np.percentile(max_drawdowns, 5)
        param_95_ret = np.percentile(final_returns, 5)
        
        median_dd = np.median(max_drawdowns)
        median_ret = np.median(final_returns)
        
        ruin_count = sum(1 for dd in max_drawdowns if dd < -0.50)
        ruin_prob = ruin_count / n_sims
        
        median_sharpe = np.median(sharpe_ratios)
        p95_sharpe = np.percentile(sharpe_ratios, 5) # Conservative side
        best_sharpe = np.max(sharpe_ratios)
        
        logger.info("All metrics calculated successfully. Returning results.")

        # Sample first 50 equity curves for UI visualization (Spaghetti Plot)
        # Assuming equity_curves list was populated in the loop
        
        return {
            "iterations": n_sims,
            "max_drawdown": {
                "p95": float(param_95_dd),
                "median": float(median_dd),
                "worst": float(np.min(max_drawdowns)),
                "best": float(np.max(max_drawdowns))
            },
            "total_return": {
                "p95": float(param_95_ret),
                "median": float(median_ret),
                "worst": float(np.min(final_returns)),
                "best": float(np.max(final_returns))
            },
            "sharpe_ratio": {
                "p95": float(p95_sharpe),
                "median": float(median_sharpe),
                "worst": float(np.min(sharpe_ratios)),
                "best": float(best_sharpe)
            },
            "ruin_probability": float(ruin_prob),
            "equity_curves": equity_curves_sample
        }
    except Exception as e:
        logger.error(f"Monte Carlo Simulation Failed: {e}")
        traceback.print_exc()
        raise e
