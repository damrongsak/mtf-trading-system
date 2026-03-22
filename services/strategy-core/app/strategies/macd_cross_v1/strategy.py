import logging
import pandas as pd
from app.logic import check_macro_bias, check_trigger, calculate_stop_loss, SignalDirection, calculate_target_price, check_rrr
from app.indicators import calculate_macd, calculate_ema

logger = logging.getLogger(__name__)

METADATA = {
    "name": "MACD Momentum Hunter",
    "description": "Institutional Momentum: H4 EMA200 Bias + M15 MACD Crossover",
    "defaults": {
        "tf_macro": "4h",
        "tf_trigger": "15min",
        "ema_period": 200,
        "fast": 12,
        "slow": 26,
        "signal": 9
    }
}

async def strategy(state, data_manager):
    """
    MACD Momentum Hunter:
    - Macro Bias: H4 EMA 200
    - Trigger: M15 MACD Crossover in direction of trend
    """
    params = state.config_json if state.config_json else {}
    symbol = state.symbol
    
    tf_macro = params.get("tf_macro", "4h")
    tf_trigger = params.get("tf_trigger", "15min")
    ema_period = int(params.get("ema_period", 200))
    fast = int(params.get("fast", 12))
    slow = int(params.get("slow", 26))
    signal_period = int(params.get("signal", 9))
    
    try:
        df_macro = data_manager.get_candles(symbol, timeframe=tf_macro)
        df_trigger = data_manager.get_candles(symbol, timeframe=tf_trigger)
        
        if df_macro.empty or df_trigger.empty:
            return None, None, None
            
    except Exception as e:
        logger.warning(f"Data fetch failed in MACD_Hunter: {e}")
        return None, None, None

    entries = pd.Series(False, index=df_trigger.index)
    exits = pd.Series(False, index=df_trigger.index)
    
    # 1. Macro Bias (H4)
    ema_h4 = calculate_ema(df_macro['close'], span=ema_period)
    current_close_h4 = df_macro['close'].iloc[-1]
    current_ema_h4 = ema_h4.iloc[-1]
    
    bias = SignalDirection.NEUTRAL
    if current_close_h4 > current_ema_h4:
        bias = SignalDirection.LONG
    elif current_close_h4 < current_ema_h4:
        bias = SignalDirection.SHORT
        
    if bias == SignalDirection.NEUTRAL:
        return entries, exits, None

    # 2. Trigger Signal (M15)
    macd_ind = calculate_macd(df_trigger['close'], fast=fast, slow=slow, signal=signal_period)
    macd_line = macd_ind.macd
    signal_line = macd_ind.signal
    
    # Check for Crossover
    is_bullish_cross = (macd_line.iloc[-1] > signal_line.iloc[-1]) and (macd_line.iloc[-2] <= signal_line.iloc[-2])
    is_bearish_cross = (macd_line.iloc[-1] < signal_line.iloc[-1]) and (macd_line.iloc[-2] >= signal_line.iloc[-2])
    
    trigger_hit = False
    if bias == SignalDirection.LONG and is_bullish_cross:
        trigger_hit = True
        entries.iloc[-1] = True
    elif bias == SignalDirection.SHORT and is_bearish_cross:
        trigger_hit = True
        exits.iloc[-1] = True
        
    if trigger_hit:
        entry_price = df_trigger['close'].iloc[-1]
        stop_loss = calculate_stop_loss(df_trigger, bias)
        target_price = calculate_target_price(df_trigger, bias, entry_price, stop_loss)
        
        # Quality Gate: RRR Check
        if check_rrr(entry_price, stop_loss, target_price, min_rrr=1.5):
            signal_dict = {
                "direction": bias.value,
                "stop_loss": stop_loss,
                "target_price": target_price,
                "reason": f"MACD Hunter: {bias.value} Momentum Crossover",
                "metadata": {
                    "bias": bias.value,
                    "ema_h4": float(current_ema_h4),
                    "macd": float(macd_line.iloc[-1]),
                    "signal": float(signal_line.iloc[-1])
                }
            }
            return entries, exits, signal_dict
            
    return entries, exits, None
