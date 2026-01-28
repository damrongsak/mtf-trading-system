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
    
    # Get Data from Manager
    # data_manager.get_data(symbol) returns a DataFrame
    data = data_manager.get_data(symbol)

    if data.empty or len(data) < 100:
        return None, None, None

    # Resampling Logic (Sync)
    try:
        # Timeframe Config
        tf_macro = params.get("tf_macro", "4h")
        tf_setup = params.get("tf_setup", "1h")
        
        # data index must be datetime
        if not isinstance(data.index, pd.DatetimeIndex):
             # Try to convert if possible or return
             df_base = data.copy()
             df_base['timestamp'] = pd.to_datetime(df_base['timestamp']) if 'timestamp' in df_base.columns else pd.to_datetime(df_base.index)
             df_base = df_base.set_index('timestamp')
        else:
             df_base = data
             
        df_setup = df_base.resample(tf_setup).agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
        }).dropna()
        
        df_macro = df_base.resample(tf_macro).agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
        }).dropna()
        
    except Exception as e:
        logger.warning(f"Resampling failed: {e}")
        return None, None, None

    # Logic (Scalar/Live mostly)
    # We construct empty series for entries/exits
    entries = pd.Series(False, index=data.index)
    exits = pd.Series(False, index=data.index)
    
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
