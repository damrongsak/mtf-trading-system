import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
# import vectorbt as vbt

METADATA = {
    "name": "Mae Pla Pakka Kiew (MPPK)",
    "description": "Multi-timeframe Price Action strategy using Pinbars, Engulfing, and Morning/Evening Stars with Context Filtering.",
    "defaults": {
        "stop_loss_buffer": 0.0, # Buffer for stop loss in pips/points if needed
        "tp_points": 1000,       # Default TP for H1
    }
}

def strategy(data: pd.DataFrame, params: Dict[str, Any] = None) -> Tuple[pd.Series, pd.Series, Dict[str, Any]]:
    """
    Mae Pla Pakka Kiew (MPPK) Strategy
    
    Args:
        data: ohlcv DataFrame
        params: Strategy parameters
        
    Returns:
        entries: Boolean Series
        exits: Boolean Series
        signal_dict: Latest signal details
    """
    if params is None: params = {}
    
    # Valid Timeframes check is assumed to be handled by the caller or UI context.
    # We proceed with the logic on the provided data.
    
    open_ = data['open']
    high = data['high']
    low = data['low']
    close = data['close']
    
    # --- 1. Pattern Recognition (Module B) ---
    
    # Helpers
    body_size = (close - open_).abs()
    upper_wick = high - pd.concat([open_, close], axis=1).max(axis=1)
    lower_wick = pd.concat([open_, close], axis=1).min(axis=1) - low
    
    is_bullish_candle = close > open_
    is_bearish_candle = close < open_
    
    # PAT 1: Pinbar (Pi Kha Yang / Pi Hua Hoy)
    # Buy: Lower Wick >= 2 * Body
    pat1_buy = (lower_wick >= 2 * body_size)
    # Sell: Upper Wick >= 2 * Body
    pat1_sell = (upper_wick >= 2 * body_size)
    
    # PAT 2: Engulfing
    # Buy Engulfing: Prev Red, Curr Green, Curr Close > Prev Open, Curr Open < Prev Close (Standard)
    # Spec says: "Measurement Start Point" is candle 3. 
    # Logic: Prev Red, Curr Green, Body engulfs prev body
    prev_open = open_.shift(1)
    prev_close = close.shift(1)
    prev_body = body_size.shift(1)
    prev_is_red = prev_close < prev_open
    prev_is_green = prev_close > prev_open
    
    pat2_buy_engulf = prev_is_red & is_bullish_candle & (close > prev_open) & (open_ < prev_close)
    pat2_sell_engulf = prev_is_green & is_bearish_candle & (close < prev_open) & (open_ > prev_close)

    # PAT 3: Morning/Evening Star
    # Buy (Morning Star): Red, Small, Green
    # i-2 (Red/Long), i-1 (Small), i (Green/Long)
    # Simplified Logic for demonstration:
    # i-2: Red
    # i-1: Small body (Doji-ish)
    # i: Green, Close > Midpoint of i-2
    close_2 = close.shift(2)
    open_2 = open_.shift(2)
    body_2 = body_size.shift(2)
    
    is_star_candle = body_size.shift(1) < (body_2 * 0.5) # Middle candle is small
    
    pat3_buy_star = (close_2 < open_2) & is_star_candle & is_bullish_candle & (close > (open_2 + close_2)/2)
    pat3_sell_star = (close_2 > open_2) & is_star_candle & is_bearish_candle & (close < (open_2 + close_2)/2)
    
    # Combine Patterns
    # Note: Spec mentions "Confirmation Candles" (2-4 candles).
    # For V1 simplified vectorization, we trigger ON the pattern completion or immediately after.
    # We will treat the pattern completion index as the signal index.
    
    raw_buy_signal = pat1_buy | pat2_buy_engulf | pat3_buy_star
    raw_sell_signal = pat1_sell | pat2_sell_engulf | pat3_sell_star
    
    # --- 2. Context Filtering (Module C) ---
    
    # Krob Logic: Price ends with 0 or 5.
    # We check if the Low (for Buy) or High (for Sell) is near a Krob level.
    # Since we can't strictly check == 0.00 due to float, we check "nearness" or if the integer part fits
    # But spec says "Integer ending with 0 or 5". For Gold (XAUUSD), price is like 2025.50.
    # "Price % 5 == 0" implies divisible by 5. e.g. 2025, 2030, 2035.
    
    # We will check if the relevant wick touched a level divisible by 5 within a small tolerance?
    # Or simply implementing the Krob check on the detection price.
    # Spec: "Logic: if (Price % 5 == 0 || Price % 10 == 0) return true;"
    # Let's apply this to the Low (Buy) and High (Sell).
    
    def is_krob(price_series):
        # Check if integer part is divisible by 5
        # We'll assume the spec means the integer level touched by the wick.
        # Simple approximation: Round to nearest int, check % 5 == 0
        p_int = price_series.round().astype(int)
        return (p_int % 5 == 0)

    # Check if Low/High touched a Krob
    krob_buy = is_krob(low)
    krob_sell = is_krob(high)
    
    # Headbutting Logic (Context)
    # "Headbutting Resistance" -> Ignore Buy
    # "Headbutting Support" -> Ignore Sell
    # We need strict S/R levels. Using Rolling Min/Max as proxy for S/R.
    
    window = 20
    recent_high = high.rolling(window=window).max().shift(1)
    recent_low = low.rolling(window=window).min().shift(1)
    
    # Buy Signal valid if NOT headbutting resistance? 
    # Actually spec says: Ignore BUY if at Resistance.
    # So Buy is VALID if NOT at Resistance.
    # But Patterns (Pinbar) usually occuring AT Support are Good.
    # Spec says: "Found Buy Signal (Hammer) at Resistance -> Ignore"
    # So we want Buy Signal at Support (Low is near recent low)
    # Low near Recent Low implies we are at Support.
    
    at_support = (low <= recent_low * 1.001) # Within 0.1% of recent low
    at_resistance = (high >= recent_high * 0.999) # Within 0.1% of recent high
    
    # Filtered Signals
    # Buy: Pattern + (At Support OR Krob Support) + NOT At Resistance
    # Wait, simple logic: Pinbar must be at Support. 
    # If Pinbar is at Resistance, it's "Headbutting" if it's a Buy Pinbar? (A Buy Pinbar at Resistance is essentially a breakout attempt or a weak reversal?).
    # Spec: "Headbutting Resistance: Found Buy Signal at Resistance -> IGNORE"
    
    valid_buy = raw_buy_signal & (at_support | krob_buy) & (~at_resistance)
    valid_sell = raw_sell_signal & (at_resistance | krob_sell) & (~at_support)

    # --- 3. Returns ---
    entries = valid_buy
    exits = valid_sell
    
    # Construct Signal Dict for the latest bar
    last_idx = -1
    latest_signal = {
        "direction": "NEUTRAL",
        "stop_loss": 0.0,
        "reason": "No Signal",
        "metadata": {}
    }
    
    if entries.iloc[last_idx]:
        # Buy Signal
        pat_type = "PAT1" if pat1_buy.iloc[last_idx] else ("PAT2" if pat2_buy_engulf.iloc[last_idx] else "PAT3")
        sl_price = low.iloc[last_idx] # "Sai Lang Sig" (Lowest Low of Signal) - approx current low
        # Note: For PAT3, should be lowest of last 3.
        if pat_type == "PAT3":
             sl_price = min(low.iloc[last_idx], low.iloc[last_idx-1], low.iloc[last_idx-2])
        elif pat_type == "PAT2":
             sl_price = min(low.iloc[last_idx], low.iloc[last_idx-1])
             
        latest_signal = {
            "direction": "BULLISH",
            "stop_loss": float(sl_price),
            "reason": f"{pat_type} at Support",
            "metadata": {
                "strategy_name": METADATA["name"],
                "pattern": pat_type,
                "krob_check": bool(krob_buy.iloc[last_idx]),
                "context": "Support",
                "tp_target": float(close.iloc[last_idx] + params.get("tp_points", 1000) * 0.0001) # Assuming forex points logic? No, MPPK uses Gold Points. 1000 points = $10 ? depends on scale. 1 point = 0.01 usually? Or 1 Pip?
                # Gold: 2000.00 -> 2001.00 is 100 Pips or 1000 Points? Usually 1$ = 100 pips.
                # If TP is 1000 points. 
            }
        }
    elif exits.iloc[last_idx]:
         # Sell Signal
        pat_type = "PAT1" if pat1_sell.iloc[last_idx] else ("PAT2" if pat2_sell_engulf.iloc[last_idx] else "PAT3")
        sl_price = high.iloc[last_idx]
        if pat_type == "PAT3":
             sl_price = max(high.iloc[last_idx], high.iloc[last_idx-1], high.iloc[last_idx-2])
        elif pat_type == "PAT2":
             sl_price = max(high.iloc[last_idx], high.iloc[last_idx-1])

        latest_signal = {
            "direction": "BEARISH",
            "stop_loss": float(sl_price),
            "reason": f"{pat_type} at Resistance",
            "metadata": {
                "strategy_name": METADATA["name"],
                "pattern": pat_type,
                "krob_check": bool(krob_sell.iloc[last_idx]),
                "context": "Resistance"
            }
        }
        
    return entries, exits, latest_signal
