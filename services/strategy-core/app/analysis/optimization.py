from typing import Dict, List, Any, Union
import vectorbt as vbt
import numpy as np
import pandas as pd
from itertools import product

def expand_param_grid(param_grid: Dict[str, Any]) -> Dict[str, List[Any]]:
    """
    Expand parameter grid where values might be defined as ranges.
    Supported formats:
    - List: [1, 2, 3]
    - Range Dict: {'start': 10, 'stop': 30, 'step': 10} (inclusive stop)
    """
    expanded_grid = {}
    for param, value in param_grid.items():
        if isinstance(value, dict) and all(k in value for k in ('start', 'stop', 'step')):
            start = float(value['start'])
            stop = float(value['stop'])
            step = float(value['step'])
            # Create range, inclusive of stop if possible
            # internal logic: use integer range if all are ints, else numpy
            if step == 0:
                 vals = [start]
            else:
                 # usage of arange with stop + step/1000 to ensure inclusivity safely
                 vals = np.arange(start, stop + step * 0.001, step).tolist()
                 
                 # If original values were ints, convert back to int for cleaner params
                 if float(start).is_integer() and float(step).is_integer():
                     vals = [int(v) for v in vals]
            expanded_grid[param] = vals
        elif isinstance(value, list):
            expanded_grid[param] = value
        else:
            # Single value fallback
            expanded_grid[param] = [value]
            
    return expanded_grid

def run_grid_search(
    data: pd.DataFrame, 
    param_grid: Dict[str, Any], 
    capital: float = 10000.0,
    fees: float = 0.0005
) -> List[Dict[str, Any]]:
    """
    Run grid search optimization using vectorbt.
    Iterative approach to avoid Numba compilation issues with broadcasting lists.
    
    Args:
        data: DataFrame with OHLCV data.
        param_grid: Dictionary of parameter names and list of values OR range dicts.
                    e.g. {'fast_window': {'start': 10, 'stop': 20, 'step': 10}}
        capital: Initial capital.
        fees: Transaction fees.
        
    Returns:
        List of dictionaries containing parameters and performance metrics, sorted by Sharpe ratio.
    """
    if data.empty:
        return []

    # Expand parameters first
    expanded_params = expand_param_grid(param_grid)

    # Optimize Fast MA, Slow MA
    fast_windows = expanded_params.get('fast_window', [10, 20])
    slow_windows = expanded_params.get('slow_window', [50, 100])
    
    close_price = data['close']
    
    # Generate indicator combinations explicitly
    combinations = list(product(fast_windows, slow_windows))
    if not combinations:
        return []
        
    results = []
    
    for f_win, s_win in combinations:
        # Cast to int to ensure VBT compatibility
        f_win = int(f_win)
        s_win = int(s_win)
        
        try:
            # Run MAs individually
            fast_ma = vbt.MA.run(close_price, window=f_win, short_name='fast')
            slow_ma = vbt.MA.run(close_price, window=s_win, short_name='slow')
            
            entries = fast_ma.ma_crossed_above(slow_ma)
            exits = fast_ma.ma_crossed_below(slow_ma)
            
            portfolio = vbt.Portfolio.from_signals(
                close_price, 
                entries, 
                exits, 
                init_cash=capital,
                fees=fees,
                freq='15m' 
            )
            
            # Extract scalar metrics
            total_return = portfolio.total_return()
            sharpe = portfolio.sharpe_ratio()
            drawdown = portfolio.max_drawdown()
            trades = portfolio.trades.count()
            
            # Handle potential scalar/series output depending on VBT version
            if hasattr(total_return, 'item'): 
                total_return = total_return.item()
            if hasattr(sharpe, 'item'): 
                sharpe = sharpe.item()
            if hasattr(drawdown, 'item'): 
                drawdown = drawdown.item()
            if hasattr(trades, 'item'): 
                trades = trades.item()

            # Handle NaN/Inf
            def clean_metric(val):
                if pd.isna(val) or np.isinf(val):
                    return 0.0
                return float(val)

            results.append({
                "params": {
                    "fast_window": f_win,
                    "slow_window": s_win
                },
                "metrics": {
                    "total_return": clean_metric(total_return),
                    "sharpe_ratio": clean_metric(sharpe),
                    "max_drawdown": clean_metric(drawdown),
                    "total_trades": int(clean_metric(trades))
                }
            })
            
        except Exception as e:
            print(f"Error for params {f_win}/{s_win}: {e}")
            continue
        
    # Sort by Sharpe Ratio descending
    results.sort(key=lambda x: x['metrics']['sharpe_ratio'], reverse=True)
    
    return results[:50] # Return top 50

