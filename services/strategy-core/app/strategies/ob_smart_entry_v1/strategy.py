import logging
import pandas as pd
import numpy as np
import time
from app.indicators import calculate_ema, calculate_atr
from app.indicators.smc import detect_order_blocks
from app.logic import SignalDirection, calculate_target_price, check_rrr

logger = logging.getLogger(__name__)

METADATA = {
    "name": "Order Block Smart Entry V1",
    "description": "Multi-Timeframe Order Block Strategy (H1 Trend, M15 OB, M5 Trigger)",
    "defaults": {
        "tf_trend": "1h",
        "tf_setup": "15min",
        "ema_trend": 60,
        "ema_trigger": 20,
        "rr_ratio": 2.0
    }
}

async def strategy(state, data_manager):
    """
    Order Block Smart Entry V1
    """
    params = state.config_json if state.config_json else METADATA["defaults"]
    symbol = state.symbol
    
    # 1. Fetch Data (Legacy Resampling Removed)
    # New Engine supports direct Timeframe requests
    try:
        tf_trend = params.get("tf_trend", "1h")
        tf_setup = params.get("tf_setup", "15min")
        tf_trigger = "5min" # Hardcoded or param

        # Standardized MTF Access
        df_h1 = data_manager.get_candles(symbol, timeframe=tf_trend)
        df_m15 = data_manager.get_candles(symbol, timeframe=tf_setup)
        df_m5 = data_manager.get_candles(symbol, timeframe=tf_trigger) # Base Trigger

        if df_h1.empty or df_m15.empty or df_m5.empty:
            return None, None, None
            
        # Use M5 as the 'primary' data for signal index
        data = df_m5
        
    except Exception as e:
        logger.warning(f"Data fetch failed for {symbol}: {e}")
        return None, None, None

    # 2. HTF Trend Bias (H1)
    # Logic: Price > EMA 60 = BULLISH, Price < EMA 60 = BEARISH
    ema_trend_p = params.get("ema_trend", 60)
    
    ema_trend = calculate_ema(df_h1['close'], span=ema_trend_p)
    
    if len(ema_trend) < 2:
        return None, None, None
        
    # Use -1 for bias (latest completed H1)
    h1_close = df_h1['close'].iloc[-1]
    h1_ema = ema_trend.iloc[-1]
    
    trend_bias = SignalDirection.NEUTRAL
    if h1_close > h1_ema:
        trend_bias = SignalDirection.BULLISH
    elif h1_close < h1_ema:
        trend_bias = SignalDirection.BEARISH
        
    if trend_bias == SignalDirection.NEUTRAL:
        return None, None, None

    # 3. MTF Setup Zone (M15 Order Blocks)
    obs = detect_order_blocks(df_m15)
    in_zone = False
    active_ob = None
    
    # Check if last M5 close is within a recent M15 OB
    m5_close = df_m5['close'].iloc[-1]
    
    # Logic: Look for the most recent OB of matching type
    for ob in reversed(obs):
        if trend_bias == SignalDirection.BULLISH and ob['type'] == 'bullish':
            # Price near or inside Bullish OB
            if m5_close >= ob['bottom'] * 0.9998: # Slack for near-misses
                in_zone = True
                active_ob = ob
                break
        elif trend_bias == SignalDirection.BEARISH and ob['type'] == 'bearish':
            # Price near or inside Bearish OB
            if m5_close <= ob['top'] * 1.0002: # Slack
                in_zone = True
                active_ob = ob
                break
                
    if not in_zone:
        return None, None, None

    # 4. LTF Entry Trigger (M5 EMA Crossover)
    ema_trigger_p = params.get("ema_trigger", 20)
    ema_trigger = calculate_ema(df_m5['close'], span=ema_trigger_p)
    
    # Crossover Logic
    prev_close = df_m5['close'].iloc[-2]
    curr_close = df_m5['close'].iloc[-1]
    prev_ema = ema_trigger.iloc[-2]
    curr_ema = ema_trigger.iloc[-1]
    
    triggered = False
    if trend_bias == SignalDirection.BULLISH:
        # Bullish Crossover: Close moves above EMA 20
        if prev_close <= prev_ema and curr_close > curr_ema:
            triggered = True
    elif trend_bias == SignalDirection.BEARISH:
        # Bearish Crossunder: Close moves below EMA 20
        if prev_close >= prev_ema and curr_close < curr_ema:
            triggered = True

    if not triggered:
        return None, None, None

    # 5. Signal Construction
    entries = pd.Series(False, index=data.index)
    exits = pd.Series(False, index=data.index)
    
    # SL from OB or ATR
    atr = calculate_atr(df_m5['high'], df_m5['low'], df_m5['close'], window=14)
    atr_val = atr.iloc[-1]
    
    if trend_bias == SignalDirection.BULLISH:
        entries.iloc[-1] = True
        # SL below OB low or ATR buffer
        stop_loss = min(active_ob['bottom'], curr_close - (atr_val * 2))
        target_price = calculate_target_price(df_m15, trend_bias, curr_close, stop_loss)
    else:
        exits.iloc[-1] = True # Strategy Engine maps True to SHORT in signals
        stop_loss = max(active_ob['top'], curr_close + (atr_val * 2))
        target_price = calculate_target_price(df_m15, trend_bias, curr_close, stop_loss)

    # Risk Reward Verification
    rr_target = params.get("rr_ratio", 2.0)
    if not check_rrr(curr_close, stop_loss, target_price, min_rrr=1.2): # Relaxed RRR for confirmation
        return None, None, None

    signal_dict = {
        "direction": "LONG" if trend_bias == SignalDirection.BULLISH else "SHORT",
        "stop_loss": float(stop_loss),
        "take_profit": float(target_price),
        "target_price": float(target_price),
        "rrr": abs(target_price - curr_close) / abs(curr_close - stop_loss),
        "reason": f"OB Smart Entry: {trend_bias.value} Trend (Price vs EMA{ema_trend_p}) + M15 OB + M5 EMA20 Trigger",
        "metadata": {
            "ob_id": active_ob['index'],
            "ob_top": active_ob['top'],
            "ob_bottom": active_ob['bottom'],
            "ema_trend": float(h1_ema)
        }
    }

    return entries, exits, signal_dict

# ---------------------------
# Vectorized Backtesting Support
# ---------------------------
def strategy_vectorized(df, params=METADATA["defaults"]):
    """
    Vectorized version of OB Smart Entry for VBT Backtesting.
    Approximates the logic: H1 Trend Bias + M5 Trigger.
    """
    # 1. Indicators
    # H1 Trend Resampling
    try:
        tf_trend = params.get("tf_trend", "1h")
        
        # Resample to H1
        # Use pandas 'B' business day or simple 'H'? 
        # Better: use rule based on input. '1h' -> 'H'
        rule = tf_trend.upper().replace("H", "H").replace("MIN", "T").replace("M", "T")
        if not rule.endswith('T') and not rule.endswith('H') and not rule.endswith('D'):
            rule = '1H'
            
        df_h1 = df.resample(rule).agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).ffill()
        
        ema_trend_p = params.get("ema_trend", 60)
        ema_h1 = calculate_ema(df_h1['close'], span=ema_trend_p)
        
        # Broadcast H1 EMA back to M5 index
        # align creates NaN where H1 index doesn't match M5 exactly? Use reindex + ffill
        ema_h1_aligned = ema_h1.reindex(df.index, method='ffill')
        
    except Exception as e:
        # Fallback if resampling fails
        ema_h1_aligned = calculate_ema(df['close'], span=60*12) # Approximate
        
    # Trend Bias
    bullish_trend = df['close'] > ema_h1_aligned
    bearish_trend = df['close'] < ema_h1_aligned
    
    # 2. Trigger (M5)
    ema_trigger_p = params.get("ema_trigger", 20)
    ema_trigger = calculate_ema(df['close'], span=ema_trigger_p)
    
    # Crossovers
    close = df['close']
    ema = ema_trigger
    
    long_trigger = (close > ema) & (close.shift(1) <= ema.shift(1))
    short_trigger = (close < ema) & (close.shift(1) >= ema.shift(1))
    
    # 3. Signals (Trend Filtered)
    entries = bullish_trend & long_trigger
    exits = bearish_trend & short_trigger # Short Entry or Exit Long
    
    return entries, exits
