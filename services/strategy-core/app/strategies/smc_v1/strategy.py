import logging
import pandas as pd
from app.logic import check_macro_bias, check_setup_zone, check_trigger, calculate_stop_loss, SignalDirection, calculate_target_price, check_rrr

logger = logging.getLogger(__name__)

METADATA = {
    "name": "Smart Money Concepts V1",
    "description": "MTF Analysis with Order Blocks and FVGs",
    "defaults": {}
}



async def strategy(state, data_manager):
    """
    SMC V1: Macro Bias (H4) + Setup Zone (H1) + Trigger (M15)
    Adapted for FleetManager (Unified Interface)
    """
    params = state.config_json if state.config_json else {}
    symbol = state.symbol
    
    # Timeframe Config
    tf_macro = params.get("tf_macro", "4h")
    tf_setup = params.get("tf_setup", "1h")
    
    # Efficient MTF Fetching using Manager's Lazy Resampling
    try:
        # 1. Base Data (M1 or whatever base is active, trigger timeframe)
        # Using M5 or M1 as base? Original used 'get_data' -> M1
        df_base = data_manager.get_candles(symbol, timeframe="1min")
        
        # 2. Setup Data
        df_setup = data_manager.get_candles(symbol, timeframe=tf_setup)
        
        # 3. Macro Data
        df_macro = data_manager.get_candles(symbol, timeframe=tf_macro)
        
        if df_base.empty or df_setup.empty or df_macro.empty:
             return None, None, None
             
    except Exception as e:
        logger.warning(f"Data fetch failed in SMC V1: {e}")
        return None, None, None

    # Logic (Scalar/Live mostly)
    # We construct empty series for entries/exits
    entries = pd.Series(False, index=df_base.index)
    exits = pd.Series(False, index=df_base.index)
    
    direction = None
    reason = ""
    signal_dict = None
    
    # Run Checks for Latest Candle
    bias = check_macro_bias(df_macro)
    
    if bias != SignalDirection.NEUTRAL:
        in_zone = check_setup_zone(df_setup, bias)
        triggered = check_trigger(df_base, bias)
        
        if in_zone and triggered:
            # Calculate Risk
            stop_loss = calculate_stop_loss(df_base, bias)
            entry_price = df_base['close'].iloc[-1]
            target_price = calculate_target_price(df_setup, bias, entry_price, stop_loss)
            
            # RRR Check
            if check_rrr(entry_price, stop_loss, target_price):
                 direction = bias.value
                 sl_val = stop_loss
                 tp_val = target_price
                 
                 # Set Series
                 if bias == SignalDirection.LONG:
                     entries.iloc[-1] = True
                 elif bias == SignalDirection.SHORT:
                     exits.iloc[-1] = True # Mapping Short to Exits
                     
                 signal_dict = {
                    "direction": direction,
                    "stop_loss": sl_val,
                    "take_profit": tp_val,
                    "target_price": tp_val,
                    "rrr": abs(tp_val - entry_price) / abs(entry_price - sl_val),
                    "reason": f"SMC Entry: {bias.value} Bias + OB + Trigger",
                    "metadata": {
                        "signal_timestamp": str(data.index[-1]),
                        "bias": bias.value
                    }
                }
            else:
                 logger.info(f"Signal filtered by RRR: Entry={entry_price}, SL={stop_loss}, TP={target_price}")

    return entries, exits, signal_dict
