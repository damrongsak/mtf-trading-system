from typing import Dict, List, Any
import vectorbt as vbt
import numpy as np
import pandas as pd
from itertools import product

def run_grid_search(
    data: pd.DataFrame, 
    param_grid: Dict[str, List[Any]], 
    capital: float = 10000.0,
    fees: float = 0.0005
) -> List[Dict[str, Any]]:
    """
    Run grid search optimization using vectorbt.
    
    Args:
        data: DataFrame with OHLCV data.
        param_grid: Dictionary of parameter names and list of values.
                    e.g. {'fast_window': [10, 20], 'slow_window': [14, 21]}
        capital: Initial capital.
        fees: Transaction fees.
        
    Returns:
        List of dictionaries containing parameters and performance metrics, sorted by Sharpe ratio.
    """
    if data.empty:
        return []

    # Optimize Fast MA, Slow MA
    fast_windows = param_grid.get('fast_window', [10, 20])
    slow_windows = param_grid.get('slow_window', [50, 100])
    
    close_price = data['close']
    
    # Generate indicator combinations explicitly
    combinations = list(product(fast_windows, slow_windows))
    if not combinations:
        return []
        
    fast_params = [c[0] for c in combinations]
    slow_params = [c[1] for c in combinations]
    
    # Run MAs with aligned parameters - this creates aligned columns for each combination
    try:
        fast_ma = vbt.MA.run(close_price, window=fast_params, short_name='fast')
        slow_ma = vbt.MA.run(close_price, window=slow_params, short_name='slow')
    except Exception as e:
        print(f"Error running vectorbt MAs: {e}")
        return []
    
    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)
    
    try:
        portfolio = vbt.Portfolio.from_signals(
            close_price, 
            entries, 
            exits, 
            init_cash=capital,
            fees=fees,
            freq='15m' # Assuming M15 for now, should be dynamic if possible
        )
    except Exception as e:
        print(f"Error creating portfolio: {e}")
        return []
    
    # Extract metrics
    results = []
    
    # helper for safe metric extraction
    def get_metric(metric_data, idx, default=0.0):
        try:
            val = metric_data.iloc[idx] if hasattr(metric_data, 'iloc') else metric_data
            if pd.isna(val) or np.isinf(val):
                return default
            return val
        except:
            return default

    # Iterate through columns (parameter combinations)
    try:
        total_return = portfolio.total_return()
        sharpe = portfolio.sharpe_ratio()
        drawdown = portfolio.max_drawdown()
        trades = portfolio.trades.count()
    except Exception as e:
        print(f"Error calculating portfolio metrics: {e}")
        return []
    
    # Iterate through combinations which align with the portfolio columns
    for i, (f_win, s_win) in enumerate(combinations):
        t_ret = get_metric(total_return, i)
        sh = get_metric(sharpe, i)
        dd = get_metric(drawdown, i)
        tr = get_metric(trades, i)
        
        results.append({
            "params": {
                "fast_window": int(f_win),
                "slow_window": int(s_win)
            },
            "metrics": {
                "total_return": float(t_ret),
                "sharpe_ratio": float(sh),
                "max_drawdown": float(dd),
                "total_trades": int(tr)
            }
        })
        
    # Sort by Sharpe Ratio descending
    results.sort(key=lambda x: x['metrics']['sharpe_ratio'], reverse=True)
    
    return results[:50] # Return top 50
