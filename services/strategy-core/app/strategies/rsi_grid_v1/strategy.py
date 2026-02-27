import logging
import pandas as pd
import numpy as np
# import vectorbt as vbt
from app.logic import calculate_stop_loss, SignalDirection

logger = logging.getLogger(__name__)

METADATA = {
    "name": "MTF RSI Grid",
    "description": "Dynamic Parameters Optimization",
    "defaults": {
        "windows": [5, 9, 14, 21, 50],
        "lookback": 100
    }
}


def strategy(data, params=None):
    """
    MTF-RSI-Grid V1: Dynamic Parameter Selection Strategy.
    """
    if params is None:
        params = {}
        
    config = METADATA["defaults"].copy()
    config.update(params)
    
    # 1. Get Data
    if data.empty or len(data) < 100:
        return None, None, None
        
    close = data['close']
    
    # 2. Config
    windows = config.get('windows', [5, 9, 14, 21, 50])
    lookback = int(config.get('lookback', 100))
    oversold_iso = 30
    overbought_iso = 70
    
    try:
        # 3. VectorBT Calculation
        import vectorbt as vbt
        rsi = vbt.RSI.run(close, window=windows).rsi
        
        # 4. Generate Signals
        entries_grid = rsi < oversold_iso
        exits_grid = rsi > overbought_iso
        
        # 5. Lookback Selection
        if len(close) < lookback:
            lookback = len(close)
            
        sim_entries = entries_grid.iloc[-lookback:]
        sim_exits = exits_grid.iloc[-lookback:]
        sim_price = close.iloc[-lookback:]
        
        import vectorbt as vbt
        pf = vbt.Portfolio.from_signals(
            sim_price, 
            sim_entries, 
            sim_exits, 
            fees=0.0,
            freq='1m'
        )
        
        perf = pf.total_return()
        best_window = perf.idxmax()
        grid_score = perf.max()
        
    except Exception as e:
        logger.warning(f"Optimization step failed: {e}")
        best_window = 14
        grid_score = 0.0
        # Re-calc fallback if VBT failed completely? 
        # Assuming rsi was calculated or we fallback
        if 'rsi' not in locals():
             import vectorbt as vbt
             rsi = vbt.RSI.run(close, window=14).rsi
             entries_grid = rsi < 30
             exits_grid = rsi > 70
             best_window = 14

    # 6. Select "Winner" Signals for Return
    if isinstance(best_window, int) and best_window in rsi.columns:
         final_entries = entries_grid[best_window]
         final_exits = exits_grid[best_window]
         current_rsi_val = rsi[best_window].iloc[-1]
    else:
         # Fallback if indices are weird
         final_entries = entries_grid.iloc[:, 0]
         final_exits = exits_grid.iloc[:, 0]
         current_rsi_val = rsi.iloc[-1, 0]

    # 7. Live Check
    is_long = final_entries.iloc[-1]
    is_short = final_exits.iloc[-1]
    
    direction = None
    reason = None
    
    if is_long:
        direction = SignalDirection.LONG
        reason = f"RSI({best_window}) < {oversold_iso}"
    elif is_short:
        direction = SignalDirection.SHORT
        reason = f"RSI({best_window}) > {overbought_iso}"
        
    signal_dict = None
    if direction:
        stop_loss = calculate_stop_loss(data, direction)
        entry_price = close.iloc[-1]
        
        dist = abs(entry_price - stop_loss)
        if direction == SignalDirection.LONG:
            take_profit = entry_price + (dist * 2)
        else:
            take_profit = entry_price - (dist * 2)
            
        signal_dict = {
            "direction": direction.value,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "target_price": take_profit,
            "rrr": 2.0,
            "reason": f"MTF-RSI-Grid: {reason} (Best Window: {best_window}, Score: {grid_score:.4f})",
            "metadata": {
                "strategy_name": "MTF-RSI-Grid",
                "description": "Dynamic RSI Optimization (Best Fit)",
                "signal_timestamp": str(data.index[-1]),
                "selected_window": int(best_window),
                "selected_threshold": oversold_iso if direction == SignalDirection.LONG else overbought_iso,
                "grid_score": float(grid_score)
            }
        }
        
    return final_entries, final_exits, signal_dict
