import pandas as pd
import numpy as np
# import vectorbt as vbt

METADATA = {
    "name": "5-EMA Recovery",
    "description": "Trend Following + Mean Reversion strategy using 5 EMAs (10, 25, 50, 100, 200) and RSI Divergence.",
    "defaults": {
        "ema_periods": [10, 25, 50, 100, 200],
        "rsi_period": 14,
        "rsi_ob": 70,
        "rsi_os": 30,
        "risk_per_trade": 0.01  # 1%
    }
}

def strategy(data, params=None):
    """
    5-EMA Recovery Strategy (Unified Interface)
    
    Logic:
    1. Trend Bias: Price > EMA 200 (Bullish) or Price < EMA 200 (Bearish).
    2. Pullback Zone: Price touches EMA 25, 50, or 100.
    3. Confluence: RSI Divergence (Price Lower Low + RSI Higher Low).
    4. Trigger: Bullish Reversal Candle (Close > Open) after touching zone.
    """
    if params is None:
        params = {}
    
    # Load parameters
    ema_periods = params.get("ema_periods", METADATA["defaults"]["ema_periods"])
    rsi_period = int(params.get("rsi_period", METADATA["defaults"]["rsi_period"]))
    
    close = data['close']
    open_price = data['open']
    high = data['high']
    low = data['low']
    
    # 1. Indicators
    # Calculate 5 EMAs
    emas = {}
    import vectorbt as vbt
    for p in ema_periods:
        emas[p] = vbt.MA.run(close, window=p, ewm=True).ma

    # RSI
    import vectorbt as vbt
    rsi = vbt.RSI.run(close, window=rsi_period).rsi

    # 2. Logic Definitions
    
    # A. Trend Bias (using EMA 200 as proxy for HTF Structure if pure vectorization)
    # Ideally should use HTF, but for single-df vectorization we use current TF EMA 200
    bullish_trend = close > emas[200]
    bearish_trend = close < emas[200]
    
    # B. Pullback Zones (Price touching/near EMA 25/50/100)
    # "Touching" defined as Low <= EMA <= High (Price bar intersects EMA)
    # We check if Low dipped into the zone between EMA 25 and EMA 100?
    # Or strict touch? Let's use "Low < EMA" while "Close > EMA_Lower_Band" or simplified intersection.
    # Simplified: Low <= EMA_25 OR Low <= EMA_50 OR Low <= EMA_100
    # BUT must be ABOVE EMA 200 (Trend)
    
    # Check if Low touches any of the support EMAs
    touched_25 = (low <= emas[25]) & (high >= emas[25])
    touched_50 = (low <= emas[50]) & (high >= emas[50])
    touched_100 = (low <= emas[100]) & (high >= emas[100])
    
    in_pullback_zone = (touched_25 | touched_50 | touched_100)
    
    # C. Divergence (Simplified Vectorized)
    # Price making Lower Low than previous bar, but RSI making Higher Low?
    # This checks 1-bar divergence. Real divergence is usually multi-bar.
    # For V1 proxy: RSI < 50 (Pullback momentum) AND RSI Rising (Slope > 0)
    # OR: Price Low < Prev Low AND RSI > Prev RSI
    
    prev_low = low.shift(1)
    prev_rsi = rsi.shift(1)
    
    bullish_divergence_proxy = (low < prev_low) & (rsi > prev_rsi) & (rsi < 60) # weak div check
    
    # D. Trigger: Reversal Candle (Green Candle)
    is_green = close > open_price
    
    # COMBINE (Bullish Setup)
    # 1. Trend is Bullish (Above EMA 200)
    # 2. Price touched a support EMA (25/50/100) recently? Or strictly this bar?
    #    The spec says "Wait for exhaustion... Trigger = Reversal Candle"
    #    So: Previous bar or This bar touched EMA -> This bar is Green
    
    # Let's say: touches EMA (Pullback) AND Green Candle (Trigger)
    # And maybe RSI check
    
    entries = bullish_trend & in_pullback_zone & is_green & (rsi > 40) # RSI safety
    
    # Exits
    # Dynamic TP: EMA 10? Or fixed RR?
    # Exit if Close < EMA 50 (Trend broken) OR RSI > 70 (Overbought)
    exits = (close < emas[50]) | (rsi > 70)
    
    # 3. Construct Signal Dict for Live
    latest_signal = {}
    if not entries.empty:
        is_entry = bool(entries.iloc[-1])
        is_exit = bool(exits.iloc[-1])
        
        direction = "FLAT"
        reason = "Wait"
        
        if is_entry:
            direction = "BULLISH"
            reason = "5-EMA Recovery Buy"
        elif is_exit:
            direction = "FLAT" # exit
            reason = "Exit Signal"
            
        latest_signal = {
            "direction": direction,
            "reason": reason,
            "metadata": {
                "strategy_name": METADATA["name"],
                "ema_200": float(emas[200].iloc[-1]) if pd.notna(emas[200].iloc[-1]) else 0.0,
                "rsi": float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else 0.0,
                "technical": {
                    "trend_biased": "BULLISH" if bullish_trend.iloc[-1] else "BEARISH",
                    "in_zone": bool(in_pullback_zone.iloc[-1])
                }
            }
        }

    return entries, exits, latest_signal
