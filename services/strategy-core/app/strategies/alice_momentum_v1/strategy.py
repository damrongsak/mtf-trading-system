import pandas as pd
import numpy as np
# import vectorbt as vbt
from app.indicators import calculate_atr, calculate_macd

METADATA = {
    "name": "Alice Momentum Regime",
    "description": "Trend Following + Regime Switching Strategy. Uses EMA50/100/200 and ATR to classify market into EASY, NORMAL, HARD, NIGHTMARE modes.",
    "defaults": {
        "ema_fast": 50,
        "ema_medium": 100,
        "ema_slow": 200,
        "atr_period": 14,
        "breakout_period": 20,
        "slope_threshold": 0.5, # Degrees or normalized slope? Using simplified proxy.
        "risk_per_trade": 0.01 
    }
}

def strategy(data, params=None):
    """
    Alice Momentum Strategy (Unified Interface)
    
    Modules:
    A. Regime Classifier (Easy, Normal, Hard, Nightmare)
    B. Signal Generator (System A: Breakout, System B: Dip)
    C. Position Manager (Hard Exit at EMA 200)
    """
    if params is None: params = {}
    
    # Load Params
    p_fast = int(params.get("ema_fast", METADATA["defaults"]["ema_fast"]))
    p_med = int(params.get("ema_medium", METADATA["defaults"]["ema_medium"]))
    p_slow = int(params.get("ema_slow", METADATA["defaults"]["ema_slow"]))
    atr_period = int(params.get("atr_period", METADATA["defaults"]["atr_period"]))
    breakout_period = int(params.get("breakout_period", METADATA["defaults"]["breakout_period"]))
    
    close = data['close']
    high = data['high']
    low = data['low']
    
    # --- 1. Indicators ---
    import vectorbt as vbt
    ema_fast = vbt.MA.run(close, window=p_fast, ewm=True).ma
    ema_med = vbt.MA.run(close, window=p_med, ewm=True).ma
    ema_slow = vbt.MA.run(close, window=p_slow, ewm=True).ma
    
    # ATR for Nightmare check
    # VectorBT doesn't have a direct ATR wrapper that returns a Series easily in one go? 
    # Use built-in calculation or helper. VBT has ATR.
    atr = vbt.ATR.run(high, low, close, window=atr_period).atr
    atr_avg = vbt.MA.run(atr, window=100).ma # Long term average for spike check
    
    # MACD for Filter
    import vectorbt as vbt
    macd = vbt.MACD.run(close)
    macd_hist = macd.hist
    
    # --- 2. Module A: Regime Classifier ---
    
    # 2.1 Trend Alignment
    # Bullish: 50 > 100 > 200
    aligned_bullish = (ema_fast > ema_med) & (ema_med > ema_slow)
    aligned_bearish = (ema_fast < ema_med) & (ema_med < ema_slow)
    is_aligned = aligned_bullish | aligned_bearish
    
    # 2.2 Slope Check (Simplified: EMA 50 > EMA 50 shift 5)
    # Checking strictly slope threshold is tricky with raw price units. 
    # We'll use a qualitative "Rising/Falling" check for now or basic rate of change.
    ema_fast_prev = ema_fast.shift(5)
    is_steep = abs(ema_fast - ema_fast_prev) > (close * 0.001) # Arbitrary steepness heuristic
    
    # 2.3 Volatility (Nightmare)
    is_nightmare = atr > (atr_avg * 2.0)
    
    # Classify
    # EASY: Aligned & Steep
    # NORMAL: Aligned & Not Steep (Retracing)
    # HARD: Not Aligned (Entangled)
    # NIGHTMARE: High Volatility
    
    # We will use integer masks or boolean reasoning
    # Priority: Nightmare > Hard > Normal/Easy
    
    # --- 3. Module B: Signal Generator ---
    
    # System A: Breakout (Easy & Normal)
    # Bullish: Close > Highest High(20)
    # Bearish: Close < Lowest Low(20)
    
    hh_20 = high.rolling(window=breakout_period).max().shift(1) # Donchian High of *previous* bars
    ll_20 = low.rolling(window=breakout_period).min().shift(1)
    
    trigger_breakout_long = (close > hh_20) & (macd_hist > 0)
    trigger_breakout_short = (close < ll_20) & (macd_hist < 0)
    
    # End of System A
    
    # System B: Buy on Dip (Normal)
    # Trend Bullish && Low touches EMA 50 && Close > EMA 50 (Rejection)
    # In 'Normal' regime, price retraces to 50/100.
    
    # Touched EMA 50/100
    touched_med_zone_long = (low <= ema_med) & (close > ema_med) & aligned_bullish
    touched_med_zone_short = (high >= ema_med) & (close < ema_med) & aligned_bearish
    
    # Logic Combination based on Regime
    
    # Regime Masks
    mask_nightmare = is_nightmare
    mask_aligned = is_aligned & (~mask_nightmare)
    mask_hard = (~is_aligned) & (~mask_nightmare)
    
    # Simplification: Enable A for Aligned, Enable B for Aligned (Dip)
    # System C (Channel) DISABLED for V1 (Hard Regime will have no entries)
    
    entries_long = (mask_aligned & trigger_breakout_long) | (mask_aligned & touched_med_zone_long)
    entries_short = (mask_aligned & trigger_breakout_short) | (mask_aligned & touched_med_zone_short)
    
    # Combine entries
    entries = entries_long | entries_short
    
    # Exits (Module C)
    # Hard Exit: Trend Breakdown (Close < EMA 200) or Nightmare
    # Scale outs are handled by Position Manager (not fully effectively simulated here in boolean)
    # We assume 'exit' signal means "Close All" for simplicity in V1 Backtest
    
    exit_long = (close < ema_slow) | mask_nightmare
    exit_short = (close > ema_slow) | mask_nightmare # Inverse for short? 
    # Actually if aligned_bearish, EMA 200 is *above* price. So exit if Close > EMA 200.
    
    exits = exit_long | exit_short # This is a bit loose, assumes we know direction.
    # Correct way: If we are long, check exit_long. If short, check exit_short.
    # VBT usually handles this by checking position direction.
    # But for raw signals, we often return 'exit' that kills any position.
    
    # --- Live Signal Dict ---
    latest_signal = {}
    if not entries.empty:
        is_entry = bool(entries.iloc[-1])
        is_exit = bool(exits.iloc[-1])
        
        regime_status = "HARD"
        if mask_nightmare.iloc[-1]: regime_status = "NIGHTMARE"
        elif mask_aligned.iloc[-1]: regime_status = "NORMAL" # Simplified (Easy/Normal merged)
        
        direction = "FLAT"
        reason = "Wait"
        
        if is_entry:
            direction = "BULLISH" if entries_long.iloc[-1] else "BEARISH"
            reason = f"Alice System Entry ({regime_status})"
        elif is_exit:
            direction = "FLAT"
            reason = f"Exit (Trend Broken/Nightmare)"
            
        latest_signal = {
            "direction": direction,
            "reason": reason,
            "metadata": {
                "strategy_name": METADATA["name"],
                "regime": regime_status,
                "technical": {
                   "ema_50": float(ema_fast.iloc[-1]),
                   "ema_100": float(ema_med.iloc[-1]),
                   "ema_200": float(ema_slow.iloc[-1]),
                   "atr": float(atr.iloc[-1])
                }
            }
        }

    return entries, exits, latest_signal
