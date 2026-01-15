import pandas as pd
import numpy as np
from enum import Enum
from typing import Optional, Dict, Any, Tuple
from app.indicators import calculate_ema, calculate_atr
from app.indicators.smc import detect_order_blocks, detect_fvg
from app.features.quant_features import QuantreoFeatures

class SignalDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


def check_macro_bias(df_h4: pd.DataFrame, ema_period: int = 200) -> SignalDirection:
    """
    Rule A: Macro Bias
    - Bullish if Close > EMA200
    - Bearish if Close < EMA200
    
    CRITICAL (Bias Prevention):
    - Uses `iloc[-2]` (Last Completed Candle) to prevent look-ahead bias if
      the DataFrame includes the current forming candle.
    """
    if len(df_h4) < ema_period + 2:
        return SignalDirection.NEUTRAL

    ema = calculate_ema(df_h4['close'], span=ema_period)
    
    # Strict Bias Prevention: Use -2 (Last Completed)
    last_close = df_h4['close'].iloc[-2] 
    last_ema = ema.iloc[-2]

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
        
    # Strict Bias Prevention: Check if LAST COMPLETED candle closed in OB
    # (Or is testing it). For entry signal, we usually want the completed candle.
    current_close = df_h1['close'].iloc[-2]
    
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

    return False

def check_trigger(df_m15: pd.DataFrame, direction: SignalDirection, rv_threshold: float = 0.7, min_volatility: float = 0.0005) -> bool:
    """
    Rule C: Trigger
    - Volatility Check (Quantreo)
    - Candle Shape (Body/Wick)
    
    CRITICAL: Strict `iloc[-2]` usage.
    """
    if len(df_m15) < 32: 
        return False

    # 1. Quantreo Volatility Filter
    df_vol = QuantreoFeatures.add_volatility_features(df_m15, window_size=30)
    # Check volatility of the CLOSED candle setup
    current_vol = df_vol['parkinson_vol_30'].iloc[-2]
    
    if current_vol < min_volatility:
        # Market too quiet, reject trade
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
    - SL = ATR(14) * M (Using Last Completed Candle)
    """
    atr = calculate_atr(df_m15['high'], df_m15['low'], df_m15['close'], window=14)
    last_atr = atr.iloc[-2]
    
    current_price = df_m15['close'].iloc[-2]
    
    dist = last_atr * atr_mult
    
    if direction == SignalDirection.BULLISH:
        return current_price - dist
    else:
        return current_price + dist

def calculate_target_price(df_h1: pd.DataFrame, direction: SignalDirection, entry_price: float, sl_price: float) -> float:
    """
    Calculate Target Price (TP) for RRR calculation.
    
    Logic:
    1. Look for nearest "Opposing" Order Block (e.g. Bearish OB for Long trade).
    2. If found, TP = Edge of OB (Bottom for Bearish, Top for Bullish).
    3. If NOT found (or too far), use a fixed 2.0R Fallback.
    """
    risk_dist = abs(entry_price - sl_price)
    
    # Fallback Target (2R)
    if direction == SignalDirection.BULLISH:
        fallback_tp = entry_price + (risk_dist * 2.0)
    else:
        fallback_tp = entry_price - (risk_dist * 2.0)
        
    # Get Order Blocks
    obs = detect_order_blocks(df_h1)
    
    nearest_ob_price = None
    
    if direction == SignalDirection.BULLISH:
        # Looking for Bearish OBs ABOVE entry
        candidates = [ob['bottom'] for ob in obs if ob['type'] == 'bearish' and ob['bottom'] > entry_price]
        if candidates:
            # Nearest one (min value > entry)
            nearest_ob_price = min(candidates)
            
    elif direction == SignalDirection.BEARISH:
        # Looking for Bullish OBs BELOW entry
        candidates = [ob['top'] for ob in obs if ob['type'] == 'bullish' and ob['top'] < entry_price]
        if candidates:
            # Nearest one (max value < entry)
            nearest_ob_price = max(candidates)
            
    # Decision: Use OB if it exists, otherwise Fallback
    # Note: Realistically, if OB is too close (< 1R), check_rrr will fail anyway.
    if nearest_ob_price is not None:
        return nearest_ob_price
        
    return fallback_tp

def check_rrr(entry_price: float, sl_price: float, tp_price: float, min_rrr: float = 1.5) -> bool:
    """
    Rule E: Risk Reward Ratio Check
    """
    risk = abs(entry_price - sl_price)
    reward = abs(tp_price - entry_price)
    
    if risk == 0:
        return False
        
    rrr = reward / risk
    
    return rrr >= min_rrr

