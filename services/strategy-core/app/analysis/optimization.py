from typing import Dict, List, Any, Union, Callable, Optional, Tuple
import vectorbt as vbt
import numpy as np
import pandas as pd
from itertools import product
import logging
import inspect
import traceback

# Setup logging
logger = logging.getLogger(__name__)

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
    fees: float = 0.0005,
    code: str = None,
    strategy_callable: Optional[Callable[[pd.DataFrame, Dict[str, Any]], Tuple[Any, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Run grid search optimization.
    Can optimize:
    1. Callable: if `strategy_callable` provided (Priority).
    2. Custom Code: if `code` is provided.
    3. Default simple MACD: if neither.
    """
    if data.empty:
        return []

    # Expand parameters
    expanded_params = expand_param_grid(param_grid)
    
    # Generate all combinations
    keys = list(expanded_params.keys())
    values = list(expanded_params.values())
    combinations = list(product(*values))
    
    if not combinations:
        return []
        
    # Limit max iterations for safety
    MAX_ITERATIONS = 50
    if len(combinations) > MAX_ITERATIONS:
        logger.warning(f"Grid search combinations {len(combinations)} exceed limit {MAX_ITERATIONS}. Truncating.")
        combinations = combinations[:MAX_ITERATIONS]

    results = []
    
    # Compile code once if provided
    strategy_func = None
    if code:
        try:
            local_scope = {}
            exec_globals = {
                'pd': pd,
                'np': np,
                'vbt': vbt,
                'vectorbt': vbt
            }
            exec(code, exec_globals, local_scope)
            if 'strategy' in local_scope:
                strategy_func = local_scope['strategy']
            else:
                logger.error("Function 'strategy' not found in custom code.")
                return []
        except Exception as e:
            logger.error(f"Failed to compile custom code: {e}")
            return []

    # Pre-calculate common data
    close_price = data['close']
    
    for combo in combinations:
        # Create current param dict
        current_params = dict(zip(keys, combo))
        
        try:
            entries = None
            exits = None
            
            if strategy_callable:
                entries, exits = strategy_callable(data, current_params)
            elif strategy_func:
                # Run custom strategy with params
                sig = inspect.signature(strategy_func)
                if 'params' in sig.parameters:
                    entries, exits = strategy_func(data, params=current_params)
                else:
                    # If user didn't update signature, they can't optimize, but we shouldn't crash
                    entries, exits = strategy_func(data)
            else:
                # Default Logic (Backward Compat) -> Hardcoded MACD optimization logic if needed
                # But typically we want to support generic params
                # For now, if no code, assume simple moving average crossover if params define 'fast_window'/'slow_window'
                f_win = int(current_params.get('fast_window', 10))
                s_win = int(current_params.get('slow_window', 20))
                
                fast_ma = vbt.MA.run(close_price, window=f_win, short_name='fast')
                slow_ma = vbt.MA.run(close_price, window=s_win, short_name='slow')
                entries = fast_ma.ma_crossed_above(slow_ma)
                exits = fast_ma.ma_crossed_below(slow_ma)

            # --- Run Portfolio (Lightweight) ---
            # Estimate freq
            freq = None
            if len(data) > 1:
                diff = data.index[1] - data.index[0]
                freq = str(int(diff.total_seconds())) + 'S'

            portfolio = vbt.Portfolio.from_signals(
                close_price, 
                entries, 
                exits, 
                init_cash=capital,
                fees=fees,
                freq=freq 
            )
            
            # --- Extract Metrics ---
            total_return = portfolio.total_return()
            sharpe = portfolio.sharpe_ratio()
            drawdown = portfolio.max_drawdown()
            trades = portfolio.trades.count()
            
            # Helper to clean scalar/numpy types
            def clean(val):
                if hasattr(val, 'item'): val = val.item()
                if pd.isna(val) or np.isinf(val): return 0.0
                return float(val)

            results.append({
                "params": current_params,
                "metrics": {
                    "total_return": clean(total_return),
                    "sharpe_ratio": clean(sharpe),
                    "max_drawdown": clean(drawdown),
                    "total_trades": int(clean(trades))
                }
            })
            
        except Exception as e:
            # traceback.print_exc()
            logger.warning(f"Optimization failed for params {current_params}: {e}")
            continue
        
    # Sort by Sharpe Ratio descending
    results.sort(key=lambda x: x['metrics']['sharpe_ratio'], reverse=True)
    
    return results
