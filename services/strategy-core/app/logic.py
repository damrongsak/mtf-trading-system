import pandas as pd
import numpy as np
from enum import Enum
from typing import Optional, Dict, Any, Tuple
from app.indicators import calculate_ema, calculate_atr
from app.smc import detect_order_blocks, detect_fvg

class SignalDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

def check_macro_bias(df_h4: pd.DataFrame, ema_period: int = 200) -> SignalDirection:
    """
    Rule A: Macro Bias
    - Bullish if Close > EMA200
    - Bearish if Close < EMA200
    Checks the last completed candle.
    """
    if len(df_h4) < ema_period + 1:
        return SignalDirection.NEUTRAL

    ema = calculate_ema(df_h4['close'], span=ema_period)
    
    # Use -1 or -2? 
    # Usually we want the 'current context'. If we are waiting for a setup in M15, 
    # the H4 bias is determined by where price IS currently relative to EMA.
    # So we use the latest close (even if forming) or last completed?
    # PRD says "Price vs EMA200". Let's use the last closed candle to be stable.
    last_close = df_h4['close'].iloc[-1] 
    last_ema = ema.iloc[-1]

    if last_close > last_ema:
        return SignalDirection.BULLISH
    elif last_close < last_ema:
        return SignalDirection.BEARISH
    
    return SignalDirection.NEUTRAL

def check_setup_zone(df_h1: pd.DataFrame, direction: SignalDirection) -> bool:
    """
    Rule B: Setup Zone (Confluence)
    - Bullish: Price in Discount Zone (Fib 0.5-0.618) of last swing + Bullish PD Array (OB/FVG)
    - Bearish: Price in Premium Zone (Fib 0.5-0.618) of last swing + Bearish PD Array
    
    SIMPLIFICATION for MVP Phase 4:
    - Detecting "Last Swing" algorithmically is complex. 
    - We will simplify to: Price is inside a detected Order Block on H1 aligned with direction.
    - Future: Add Fib retracement logic.
    """
    if direction == SignalDirection.NEUTRAL:
        return False

    # Get recent Order Blocks
    # We only care if CURRENT price is inside an OB.
    obs = detect_order_blocks(df_h1)
    
    if not obs:
        return False
        
    current_close = df_h1['close'].iloc[-1]
    
    for ob in obs:
        # Check alignment
        if direction == SignalDirection.BULLISH and ob['type'] == 'bullish':
             # Price inside OB range? (Top/Bottom)
             # Bullish OB is usually a 'Down' candle, so Top is Open, Bottom is Close
             if ob['bottom'] <= current_close <= ob['top']:
                 return True
                 
        elif direction == SignalDirection.BEARISH and ob['type'] == 'bearish':
             # Bearish OB is 'Up' candle. Top is Close, Bottom is Open
             if ob['bottom'] <= current_close <= ob['top']:
                 return True
                 
    return False

def check_trigger(df_m15: pd.DataFrame, direction: SignalDirection, rv_threshold: float = 0.7) -> bool:
    """
    Rule C: Trigger
    - 15m Candle Validation.
    - Bullish: Strong Green Candle (Body > Wick).
    - Bearish: Strong Red Candle.
    - Body-to-Wick Ratio (Rv) > threshold.
    """
    if len(df_m15) < 2:
        return False
        
    # We check the LAST COMPLETED candle for the trigger shape
    candle = df_m15.iloc[-2]
    
    open_price = candle['open']
    close_price = candle['close']
    high = candle['high']
    low = candle['low']
    
    body = abs(close_price - open_price)
    range_len = high - low
    
    if range_len == 0:
        return False
        
    rv = body / range_len
    
    if rv < rv_threshold:
        return False
        
    # Check Direction
    if direction == SignalDirection.BULLISH:
        # Must be Green
        return close_price > open_price
    elif direction == SignalDirection.BEARISH:
        # Must be Red
        return close_price < open_price
        
    return False

def calculate_stop_loss(df_m15: pd.DataFrame, direction: SignalDirection, atr_mult: float = 1.75) -> float:
    """
    Rule D: Risk Management (Stop Loss)
    - SL = ATR(14) * M
    """
    atr = calculate_atr(df_m15['high'], df_m15['low'], df_m15['close'], window=14)
    last_atr = atr.iloc[-1]
    
    current_price = df_m15['close'].iloc[-1]
    
    dist = last_atr * atr_mult
    
    if direction == SignalDirection.BULLISH:
        return current_price - dist
    else:
        return current_price + dist
