import numpy as np
import pandas as pd
from typing import Dict, List, Any
import logging
import traceback

logger = logging.getLogger(__name__)

def run_monte_carlo(
    trades: List[Dict[str, Any]], 
    n_sims: int = 1000, 
    mode: str = "bootstrap",
    ruin_threshold: float = -0.50
) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation on a list of trades to determine robust performance metrics.
    
    Args:
        trades: List of trade objects.
        n_sims: Number of simulations to run.
        mode: 'bootstrap' (with replacement) or 'permutation' (without replacement).
        ruin_threshold: Fraction of loss considered as ruin (default -50%).
        
    Returns:
        Dictionary with confidence intervals for metrics.
    """
    try:
        logger.info(f"Starting Monte Carlo ({mode}) simulation with {n_sims} iterations.")
        if not trades:
            logger.warning("No trades provided for Monte Carlo.")
            return {}
            
        # Extract trade returns
        returns = []
        for t in trades:
            if 'return_pct' in t:
                returns.append(t['return_pct'])
            elif 'pnl_percent' in t:
                returns.append(t['pnl_percent'] / 100.0)
            elif 'pnl' in t and 'entry_price' in t:
                 # Standardize lot to units if missing
                 units = t.get('units', t.get('lot', 0.01) * 100000)
                 notional = t['entry_price'] * units
                 returns.append(t['pnl'] / notional if notional > 0 else 0)
        
        if not returns:
            logger.warning("No valid returns found in trades.")
            return {}
            
        returns_array = np.array(returns)
        n_trades = len(returns_array)
        
        rng = np.random.default_rng()
        
        final_returns = []
        max_drawdowns = []
        sharpe_ratios = []
        equity_curves_sample = [] 
        
        # Performance Tracking
        for idx in range(n_sims):
            if mode == "bootstrap":
                # Sample with replacement
                sim_returns = rng.choice(returns_array, size=n_trades, replace=True)
            else:
                # Sample without replacement (Permutation)
                sim_returns = rng.permutation(returns_array)
            
            # Equity Curve
            equity_curve = np.cumprod(1 + sim_returns)
            final_returns.append(equity_curve[-1] - 1)
            
            # Max Drawdown
            padded_equity = np.insert(equity_curve, 0, 1.0)
            running_max = np.maximum.accumulate(padded_equity)
            dd = (padded_equity - running_max) / running_max
            max_drawdowns.append(np.min(dd))
            
            # Sharpe
            mean_ret = np.mean(sim_returns)
            std_ret = np.std(sim_returns)
            sharpe = (mean_ret / std_ret) * np.sqrt(n_trades) if std_ret > 0 else 0
            sharpe_ratios.append(sharpe)
            
            # Store sample curves for visualization (first 50)
            if idx < 50:
                 equity_curves_sample.append(padded_equity.tolist())
            
        # Calculate Distributions
        param_95_dd = np.percentile(max_drawdowns, 5)
        param_95_ret = np.percentile(final_returns, 5)
        param_95_sharpe = np.percentile(sharpe_ratios, 5)
        
        ruin_count = sum(1 for dd in max_drawdowns if dd <= ruin_threshold)
        
        return {
            "iterations": n_sims,
            "mode": mode,
            "max_drawdown": {
                "p95": float(param_95_dd),
                "median": float(np.median(max_drawdowns)),
                "worst": float(np.min(max_drawdowns)),
                "best": float(np.max(max_drawdowns))
            },
            "total_return": {
                "p95": float(param_95_ret),
                "median": float(np.median(final_returns)),
                "worst": float(np.min(final_returns)),
                "best": float(np.max(final_returns))
            },
            "sharpe_ratio": {
                "p95": float(param_95_sharpe),
                "median": float(np.median(sharpe_ratios)),
                "worst": float(np.min(sharpe_ratios)),
                "best": float(np.max(sharpe_ratios))
            },
            "ruin_probability": float(ruin_count / n_sims),
            "equity_curves": equity_curves_sample,
            "confidence_bands": {
                "upper_95": np.percentile(equity_curves_sample, 95, axis=0).tolist() if equity_curves_sample else [],
                "lower_05": np.percentile(equity_curves_sample, 5, axis=0).tolist() if equity_curves_sample else []
            }
        }
    except Exception as e:
        logger.error(f"Monte Carlo Simulation Failed: {e}")
        traceback.print_exc()
        raise e
    except Exception as e:
        logger.error(f"Monte Carlo Simulation Failed: {e}")
        traceback.print_exc()
        raise e
