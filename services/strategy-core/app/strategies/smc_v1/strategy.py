import logging
import pandas as pd
from app.logic import check_macro_bias, check_setup_zone, check_trigger, calculate_stop_loss, SignalDirection, calculate_target_price, check_rrr

logger = logging.getLogger(__name__)

async def strategy(state, data_manager):
    """
    SMC V1: Macro Bias (H4) + Setup Zone (H1) + Trigger (M15)
    """
    symbol = state.symbol
    timeframe = state.timeframe # e.g. M15
    
    # 1. Get Data
    df_base = data_manager.get_data(symbol)
    
    if df_base.empty or len(df_base) < 100:
        return None

    # Resampling Logic
    try:
        df_h1 = df_base.set_index('timestamp').resample('1h').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
        }).dropna().reset_index()
        
        df_h4 = df_base.set_index('timestamp').resample('4h').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
        }).dropna().reset_index()
    except Exception as e:
        logger.warning(f"Resampling failed for {symbol}: {e}")
        return None

    # Logic
    bias = check_macro_bias(df_h4)
    if bias == SignalDirection.NEUTRAL:
        return None

    if not check_setup_zone(df_h1, bias):
        return None

    if not check_trigger(df_base, bias):
        return None

    stop_loss = calculate_stop_loss(df_base, bias)
    
    # --- RRR Filter ---
    entry_price = df_base['close'].iloc[-1]
    target_price = calculate_target_price(df_h1, bias, entry_price, stop_loss)
    
    if not check_rrr(entry_price, stop_loss, target_price):
         logger.info(f"Signal filtered by RRR: Entry={entry_price}, SL={stop_loss}, TP={target_price}")
         return None

    return {
        "direction": bias.value,
        "stop_loss": stop_loss,
        "take_profit": target_price,
        "target_price": target_price,
        "rrr": abs(target_price - entry_price) / abs(entry_price - stop_loss),
        "reason": f"SMC Entry: {bias.value} Bias + OB + Trigger",
        "metadata": {
            "signal_timestamp": str(df_base['timestamp'].iloc[-1]) if 'timestamp' in df_base.columns else str(df_base.index[-1]),
            "bias": bias.value
        }
    }
