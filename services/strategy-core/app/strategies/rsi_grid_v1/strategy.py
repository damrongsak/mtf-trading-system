import logging
import pandas as pd
import numpy as np
import vectorbt as vbt
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

async def strategy(state, data_manager):
    """
    MTF-RSI-Grid V1: Dynamic Parameter Selection Strategy.
    Uses VectorBT to test multiple RSI windows and thresholds in real-time.
    """
    symbol = state.symbol
    timeframe = state.timeframe
    
    # 1. Get Data
    df_base = data_manager.get_data(symbol)
    if df_base.empty or len(df_base) < 100:
        return None
        
    close = df_base['close']
    
    # 2. Configuration Grid
    # We test a grid of RSI windows
    windows = [5, 9, 14, 21, 50]
    
    # Thresholds could also be a grid, but let's stick to standard 30/70 for simplicity 
    # or simple dynamic bands to keep dimension 2D (time x window) instead of 3D.
    oversold_iso = 30
    overbought_iso = 70
    
    # 3. VectorBT Calculation (Broadcasting)
    # This runs RSI for ALL windows at once
    # Result shape: (Rows, len(windows))
    try:
        rsi = vbt.RSI.run(close, window=windows).rsi
    except Exception as e:
        logger.error(f"VBT RSI Grid calculation failed: {e}")
        return None
        
    # 4. Generate Signals (Hypothetical)
    entries = rsi < oversold_iso
    exits = rsi > overbought_iso
    
    # 5. Determine Best Parameter Set (Lookback Selection)
    # We want to know which 'window' performed best recently (e.g. last 100 candles)
    # We can simulate a portfolio for the lookback period
    lookback = 100
    if len(close) < lookback:
        lookback = len(close)
        
    # Slice the last 'lookback' period for simulation
    # Note: VBT handles slicing efficiently
    # We simulate 'from_signals'
    # fees=0.0 to focus on raw signal quality
    
    try:
        # We need to run simulation on the recent slice to see which param set is 'hot'
        # A simple approximation is "Total Return" of the signal trail
        # Or even simpler: Win Rate of recent signals.
        # Let's use Portfolio for robustness.
        
        sim_entries = entries.iloc[-lookback:]
        sim_exits = exits.iloc[-lookback:]
        sim_price = close.iloc[-lookback:]
        
        pf = vbt.Portfolio.from_signals(
            sim_price, 
            sim_entries, 
            sim_exits, 
            fees=0.0,
            freq='1m' # Dummy freq
        )
        
        # Get Total Return per Window
        # This returns a Series indexed by Window
        perf = pf.total_return()
        
        # Find the winner
        best_window = perf.idxmax()
        grid_score = perf.max()
        
        # If best return is negative, maybe we shouldn't trade at all?
        # For this V1, we take the best relative performer.
        
    except Exception as e:
        logger.warning(f"Optimization step failed: {e}")
        # Fallback to standard 14
        best_window = 14
        grid_score = 0.0

    # 6. Check Current Signal for the Winner
    # We look at the LAST row of the Winner's column
    # rsi is a DataFrame where columns are windows
    
    current_rsi_val = rsi[best_window].iloc[-1]
    is_long = entries[best_window].iloc[-1]
    is_short = exits[best_window].iloc[-1] # RSI Mean Reversion: 'Exit' acts as Short Entry in reversal strategies?
    # standard RSI is Long Only (Oversold=Buy). 
    # But usually > 70 can be Short.
    # Let's define Direction based on thresholds.
    
    direction = None
    reason = None
    
    if is_long:
        direction = SignalDirection.LONG
        reason = f"RSI({best_window}) < {oversold_iso}"
    elif is_short:
        # If we treat > 70 as Short
        direction = SignalDirection.SHORT
        reason = f"RSI({best_window}) > {overbought_iso}"
        
    if not direction:
        return None
        
    # 7. Risk Management (ATR Based)
    # Calculate ATR for SL using standard 14 regardless of RSI window
    # or match the window? Standard 14 is safer for ATR.
    
    # We need ATR logic. 
    # Let's assume we use a standard 1.5x ATR SL
    
    # Import locally to avoid circular if needed, or use logic util
    # We don't have ATR in 'data_manager' directly usually, need calculation.
    # Let's use simple logic helper if available, or calc generic
    # For now, simple % based fallback if ATR not handy, 
    # BUT we should use `calculate_stop_loss` if possible.
    
    stop_loss = calculate_stop_loss(df_base, direction)
    entry_price = close.iloc[-1]
    
    # Simple 1:2 RR
    dist = abs(entry_price - stop_loss)
    if direction == SignalDirection.LONG:
        take_profit = entry_price + (dist * 2)
    else:
        take_profit = entry_price - (dist * 2)
        
    return {
        "direction": direction.value,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "target_price": take_profit,
        "rrr": 2.0,
        "reason": f"MTF-RSI-Grid: {reason} (Best Window: {best_window}, Score: {grid_score:.4f})",
        "metadata": {
            "strategy_name": "MTF-RSI-Grid",
            "description": "Dynamic RSI Optimization (Best Fit)",
            "signal_timestamp": str(df_base.index[-1]),
            "selected_window": int(best_window),
            "selected_threshold": oversold_iso if direction == SignalDirection.LONG else overbought_iso,
            "grid_score": float(grid_score)
        }
    }
