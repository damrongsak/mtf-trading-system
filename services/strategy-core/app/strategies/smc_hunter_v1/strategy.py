import logging
import pandas as pd
from app.logic import check_macro_bias, check_hunter_setup, check_hunter_trigger, calculate_stop_loss, SignalDirection, calculate_target_price, check_rrr

logger = logging.getLogger(__name__)

METADATA = {
    "name": "SMC Hunter V1",
    "description": "Liquidity Raid Strategy (Phase 64) - Waits for retail stops before entering",
    "defaults": {
        "tf_macro": "4h",
        "tf_setup": "1h", 
        "tf_trigger": "15min"
    }
}

async def strategy(state, data_manager):
    """
    SMC Hunter V1: Institutional 'Hunter Mode' (Phase 64)
    - Macro Bias (H4)
    - Setup: Confirmed Liquidity Raid/Sweep (H1)
    - Trigger: V-Shape Rejection back into range (M15)
    """
    params = state.config_json if state.config_json else {}
    symbol = state.symbol
    
    tf_macro = params.get("tf_macro", "4h")
    tf_setup = params.get("tf_setup", "1h")
    tf_trigger = params.get("tf_trigger", "15min")
    
    try:
        df_trigger = data_manager.get_candles(symbol, timeframe=tf_trigger)
        df_setup = data_manager.get_candles(symbol, timeframe=tf_setup)
        df_macro = data_manager.get_candles(symbol, timeframe=tf_macro)
        
        if df_trigger.empty or df_setup.empty or df_macro.empty:
             return None, None, None
             
    except Exception as e:
        logger.warning(f"Data fetch failed in SMC Hunter: {e}")
        return None, None, None

    entries = pd.Series(False, index=df_trigger.index)
    exits = pd.Series(False, index=df_trigger.index)
    
    # Run Checks
    bias = check_macro_bias(df_macro)
    
    if bias != SignalDirection.NEUTRAL:
        # 1. Hunter Setup: Check for Liquidity Raid (Sweep) on Setup Timeframe
        # We look for 'judas' or 'sweep' labels that align with our bias.
        raid_confirmed = check_hunter_setup(df_setup, bias)
        
        # 2. Hunter Trigger: Check for V-Shape Rejection on Trigger Timeframe
        # The trigger candle must be closing back into the range after the raid.
        trigger_confirmed = check_hunter_trigger(df_trigger, bias)
        
        if raid_confirmed and trigger_confirmed:
            entry_price = df_trigger['close'].iloc[-1]
            
            # Risk Management
            stop_loss = calculate_stop_loss(df_trigger, bias)
            target_price = calculate_target_price(df_setup, bias, entry_price, stop_loss)
            
            # RRR Threshold Check
            if check_rrr(entry_price, stop_loss, target_price, min_rrr=2.0):
                if bias == SignalDirection.LONG:
                    entries.iloc[-1] = True
                elif bias == SignalDirection.SHORT:
                    exits.iloc[-1] = True
                    
                signal_dict = {
                    "direction": bias.value,
                    "stop_loss": stop_loss,
                    "target_price": target_price,
                    "rrr": abs(target_price - entry_price) / abs(entry_price - stop_loss),
                    "reason": f"SMC Hunter: {bias.value} Raid Confirmed + Reject",
                    "metadata": {
                        "bias": bias.value,
                        "setup_tf": tf_setup,
                        "trigger_tf": tf_trigger,
                        "labels": df_trigger['ai_labels'].iloc[-1] if 'ai_labels' in df_trigger.columns else {}
                    }
                }
                return entries, exits, signal_dict

    return entries, exits, None
