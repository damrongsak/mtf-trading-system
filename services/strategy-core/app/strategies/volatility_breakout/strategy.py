import logging
import pandas as pd
import numpy as np
from app.indicators.volatility import calculate_atr, calculate_adr
from app.indicators import calculate_ema
from app.logic import check_macro_bias, check_trigger, calculate_stop_loss, SignalDirection, calculate_target_price, check_rrr

logger = logging.getLogger(__name__)

METADATA = {
    "name": "Volatility Breakout Hunter",
    "description": "Institutional Breakout: H1 Compression + M15 Keltner Breakout",
    "defaults": {
        "tf_macro": "1h",
        "tf_trigger": "15min",
        "atr_period": 14,
        "atr_smooth_period": 20,
        "adr_period": 20,
        "keltner_mult": 2.0
    }
}

async def strategy(state, data_manager):
    """
    Volatility Breakout Hunter:
    - Macro Bias: H1 Volatility Compression (ATR < ATR_SMA)
    - Trigger: M15 Breakout of Keltner Channel
    """
    params = state.config_json if state.config_json else {}
    symbol = state.symbol
    
    tf_macro = params.get("tf_macro", "1h")
    tf_trigger = params.get("tf_trigger", "15min")
    atr_period = int(params.get("atr_period", 14))
    atr_smooth_period = int(params.get("atr_smooth_period", 20))
    adr_period = int(params.get("adr_period", 20))
    keltner_mult = float(params.get("keltner_mult", 2.0))
    
    try:
        df_macro = data_manager.get_candles(symbol, timeframe=tf_macro)
        df_trigger = data_manager.get_candles(symbol, timeframe=tf_trigger)
        
        if df_macro.empty or df_trigger.empty:
            return None, None, None
            
    except Exception as e:
        logger.warning(f"Data fetch failed in Volatility_Hunter: {e}")
        return None, None, None

    entries = pd.Series(False, index=df_trigger.index)
    exits = pd.Series(False, index=df_trigger.index)
    
    # 1. Macro Compression (H1)
    atr_h1 = calculate_atr(df_macro['high'], df_macro['low'], df_macro['close'], window=atr_period)
    atr_sma_h1 = atr_h1.rolling(window=atr_smooth_period).mean()
    
    is_compressed = atr_h1.iloc[-1] < atr_sma_h1.iloc[-1]
    
    if not is_compressed:
        return entries, exits, None

    # 2. Trigger Signal (M15)
    # Keltner Channels on M15
    close_m15 = df_trigger['close']
    ema_m15 = calculate_ema(close_m15, span=20)
    atr_m15 = calculate_atr(df_trigger['high'], df_trigger['low'], close_m15, window=atr_period)
    
    upper_channel = ema_m15 + (keltner_mult * atr_m15)
    lower_channel = ema_m15 - (keltner_mult * atr_m15)
    
    current_close = close_m15.iloc[-1]
    last_close = close_m15.iloc[-2]
    
    direction = SignalDirection.NEUTRAL
    if current_close > upper_channel.iloc[-1] and last_close <= upper_channel.iloc[-2]:
        direction = SignalDirection.LONG
        entries.iloc[-1] = True
    elif current_close < lower_channel.iloc[-1] and last_close >= lower_channel.iloc[-2]:
        direction = SignalDirection.SHORT
        exits.iloc[-1] = True
        
    if direction != SignalDirection.NEUTRAL:
        stop_loss = calculate_stop_loss(df_trigger, direction)
        # ADR based target
        adr_val = calculate_adr(df_trigger['high'], df_trigger['low'], window=adr_period).iloc[-1]
        target_price = current_close + adr_val if direction == SignalDirection.LONG else current_close - adr_val
        
        if check_rrr(current_close, stop_loss, target_price, min_rrr=1.2):
            signal_dict = {
                "direction": direction.value,
                "stop_loss": stop_loss,
                "target_price": target_price,
                "reason": f"Volatility Breakout: {direction.value} Expansion from H1 Compression",
                "metadata": {
                    "compression_ratio": float(atr_h1.iloc[-1] / atr_sma_h1.iloc[-1]),
                    "atr_m15": float(atr_m15.iloc[-1]),
                    "adr_target": float(adr_val)
                }
            }
            return entries, exits, signal_dict
            
    return entries, exits, None
