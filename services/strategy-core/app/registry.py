
import logging
from typing import Optional, Dict
import pandas as pd
from app.logic import check_macro_bias, check_setup_zone, check_trigger, calculate_stop_loss, SignalDirection

logger = logging.getLogger(__name__)

# --- Template Functions ---

async def smc_v1_strategy(state, data_manager):
    """
    SMC V1: Macro Bias (H4) + Setup Zone (H1) + Trigger (M15)
    """
    symbol = state.symbol
    timeframe = state.timeframe # e.g. M15
    
    # 1. Get Data from Shared Manager
    # We need M15 (Base), H1, H4.
    # The SharedMarketDataManager (passed as arg) should give us data. (Assuming it has a get_data(symbol, timeframe) method or similar)
    # But wait, shared data manager returns 'DataFrame for Symbol' usually containing all ticks or pre-resampled?
    # For MVP SharedMarketDataManager returns the main buffer (e.g. M15/M1 source).
    
    # Let's assume data_manager.get_data(symbol) returns the base timeframe DF.
    df_base = data_manager.get_data(symbol)
    
    if df_base.empty or len(df_base) < 100:
        return None

    # Resampling Logic (mirrored from old engine.py)
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

    # For trigger we use base timeframe (M15)
    if not check_trigger(df_base, bias):
        return None

    stop_loss = calculate_stop_loss(df_base, bias)

    return {
        "direction": bias.value,
        "stop_loss": stop_loss,
        "reason": f"SMC Entry: {bias.value} Bias + OB + Trigger"
    }

async def macd_cross_strategy(state, data_manager):
    """
    Simple MACD Crossover
    """
    # Placeholder for MACD logic
    return None

# --- Registry ---

class StrategyRegistry:
    _strategies = {
        "SMC_V1": smc_v1_strategy,
        "MACD_CROSS_V1": macd_cross_strategy
    }
    
    _metadata = {
        "SMC_V1": {
            "name": "Smart Money Concepts V1",
            "description": "MTF Analysis with Order Blocks and FVGs",
            "defaults": {} 
        },
        "MACD_CROSS_V1": {
            "name": "MACD Crossover",
            "description": "Standard Momentum Strategy",
            "defaults": {}
        }
    }

    @classmethod
    def get_strategy_logic(cls, template_id: str):
        return cls._strategies.get(template_id)

    @classmethod
    def get_metadata(cls, template_id: str):
        return cls._metadata.get(template_id)

    @classmethod
    def list_templates(cls):
        return [{"id": k, **v} for k, v in cls._metadata.items()]

