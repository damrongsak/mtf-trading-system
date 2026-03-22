import logging
import pandas as pd
from app.logic import check_macro_bias, check_trigger, calculate_stop_loss, SignalDirection, calculate_target_price, check_rrr
from app.indicators import calculate_ema, calculate_rsi

logger = logging.getLogger(__name__)

METADATA = {
    "name": "EMA RSI Trend Hunter",
    "description": "Institutional Trend-Following: H4 EMA200 Bias + M15 RSI Exhaustion",
    "defaults": {
        "tf_macro": "4h",
        "tf_trigger": "15min",
        "ema_period": 200,
        "rsi_period": 14,
        "rsi_oversold": 30,
        "rsi_overbought": 70
    }
}

async def strategy(state, data_manager):
    """
    EMA RSI Trend Hunter:
    - Macro Bias: H4 EMA 200
    - Trigger: M15 RSI Overbought/Oversold in direction of trend
    """
    params = state.config_json if state.config_json else {}
    symbol = state.symbol
    
    tf_macro = params.get("tf_macro", "4h")
    tf_trigger = params.get("tf_trigger", "15min")
    ema_period = int(params.get("ema_period", 200))
    rsi_period = int(params.get("rsi_period", 14))
    
    try:
        df_macro = data_manager.get_candles(symbol, timeframe=tf_macro)
        df_trigger = data_manager.get_candles(symbol, timeframe=tf_trigger)
        
        if df_macro.empty or df_trigger.empty:
            return None, None, None
            
    except Exception as e:
        logger.warning(f"Data fetch failed in EMA_RSI: {e}")
        return None, None, None

    entries = pd.Series(False, index=df_trigger.index)
    exits = pd.Series(False, index=df_trigger.index)
    
    # 1. Macro Bias (H4)
    # Re-calculate EMA on H4 for precise bias
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
    # RSI on M15
    rsi_m15 = calculate_rsi(df_trigger['close'], window=rsi_period)
    current_rsi = rsi_m15.iloc[-1]
    
    rsi_oversold = int(params.get("rsi_oversold", 30))
    rsi_overbought = int(params.get("rsi_overbought", 70))
    
    trigger_hit = False
    if bias == SignalDirection.LONG and current_rsi < rsi_oversold:
        trigger_hit = True
        entries.iloc[-1] = True
    elif bias == SignalDirection.SHORT and current_rsi > rsi_overbought:
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
                "reason": f"EMA RSI: {bias.value} Trend + RSI Exhaustion ({current_rsi:.2f})",
                "metadata": {
                    "bias": bias.value,
                    "ema_h4": float(current_ema_h4),
                    "rsi_m15": float(current_rsi)
                }
            }
            return entries, exits, signal_dict
            
    return entries, exits, None
