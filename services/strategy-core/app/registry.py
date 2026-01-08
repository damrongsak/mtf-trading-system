
import asyncio
import logging
from typing import Optional, Dict
import pandas as pd
from app.logic import check_macro_bias, check_setup_zone, check_trigger, calculate_stop_loss, SignalDirection, calculate_target_price, check_rrr
from app.indicators import calculate_ema, calculate_rsi, calculate_macd

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
    
    # --- RRR Filter ---
    entry_price = df_base['close'].iloc[-1] # Current price (or approximate entry)
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
        "reason": f"SMC Entry: {bias.value} Bias + OB + Trigger"
    }

async def macd_cross_strategy(state, data_manager):
    """
    Simple MACD Crossover
    - Bullish: MACD line crosses ABOVE Signal line
    - Bearish: MACD line crosses BELOW Signal line
    """
    symbol = state.symbol
    config = state.config_json if hasattr(state, 'config_json') else {}
    fast = config.get('fast', 12)
    slow = config.get('slow', 26)
    signal_period = config.get('signal', 9)
    
    df = data_manager.get_data(symbol)
    if df.empty or len(df) < slow + signal_period + 10:
        return None
        
    try:
        close = df['close']
        
        # Calculate MACD
        # Returns object with .macd and .signal properties (pandas Series)
        macd_ind = calculate_macd(close, fast=fast, slow=slow, signal=signal_period)
        
        macd_line = macd_ind.macd
        signal_line = macd_ind.signal
        
        # Check current and previous values
        curr_macd = macd_line.iloc[-1]
        curr_sig = signal_line.iloc[-1]
        
        prev_macd = macd_line.iloc[-2]
        prev_sig = signal_line.iloc[-2]
        
        direction = None
        reason = ""
        
        # Bullish Crossover: Prev MACD < Prev Sig AND Curr MACD > Curr Sig
        if prev_macd < prev_sig and curr_macd > curr_sig:
            direction = "BULLISH"
            reason = f"MACD Bullish Crossover (MACD {curr_macd:.4f} > Sig {curr_sig:.4f})"
        
        # Bearish Crossover: Prev MACD > Prev Sig AND Curr MACD < Curr Sig
        elif prev_macd > prev_sig and curr_macd < curr_sig:
             direction = "BEARISH"
             reason = f"MACD Bearish Crossover (MACD {curr_macd:.4f} < Sig {curr_sig:.4f})"
             
        if direction:
             # Stop Loss: Recent Swing Low/High or simple ATR based?
             # For simplicity, using lowest low / highest high of last 5 bars
             sl_price = df['low'].iloc[-5:].min() if direction == "BULLISH" else df['high'].iloc[-5:].max()
             
             return {
                "direction": direction,
                "stop_loss": sl_price,
                "reason": reason
            }
            
    except Exception as e:
        logger.error(f"Error in MACD Strategy for {symbol}: {e}")
        return None
        
    return None

async def ema_rsi_strategy(state, data_manager):
    """
    EMA (200) + RSI (14) Strategy
    - Bullish: Price > EMA and RSI < 30 (Oversold -> Buy Dip)
    - Bearish: Price < EMA and RSI > 70 (Overbought -> Sell Rally)
    """
    symbol = state.symbol
    # Get configuration from state or default
    config = state.config_json if hasattr(state, 'config_json') else {}
    ema_period = config.get('ema_period', 200)
    rsi_period = config.get('rsi_period', 14)
    rsi_overbought = config.get('rsi_overbought', 70)
    rsi_oversold = config.get('rsi_oversold', 30)
    
    df = data_manager.get_data(symbol)
    if df.empty or len(df) < ema_period + 10:
        return None
        
    # Calculate Indicators
    # Ensure 'close' is used
    try:
        close = df['close']
        
        # Calculate EMA
        ema = calculate_ema(close, span=ema_period)
        
        # Calculate RSI
        rsi = calculate_rsi(close, window=rsi_period)
        
        # Check latest candle (last completed candle usually, or current if live tick)
        # Using -1 for latest available data point
        current_price = close.iloc[-1]
        current_ema = ema.iloc[-1]
        current_rsi = rsi.iloc[-1]
        
        # Logic
        direction = None
        reason = ""
        
        # 1. Trend Filter
        is_uptrend = current_price > current_ema
        is_downtrend = current_price < current_ema
        
        # 2. Trigger
        if is_uptrend and current_rsi < rsi_oversold:
            direction = "BULLISH"
            reason = f"Uptrend (Price {current_price:.2f} > EMA {current_ema:.2f}) + RSI Oversold ({current_rsi:.2f})"
        elif is_downtrend and current_rsi > rsi_overbought:
            direction = "BEARISH"
            reason = f"Downtrend (Price {current_price:.2f} < EMA {current_ema:.2f}) + RSI Overbought ({current_rsi:.2f})"
            
        if direction:
             return {
                "direction": direction,
                "stop_loss": current_ema, # Simple SL at EMA
                "reason": reason
            }
            
    except Exception as e:
        logger.error(f"Error in EMA_RSI strategy for {symbol}: {e}")
        return None
        
    return None

# --- Registry ---

class StrategyRegistry:
    _strategies = {
        "SMC_V1": smc_v1_strategy,
        "MACD_CROSS_V1": macd_cross_strategy,
        "EMA_RSI_V1": ema_rsi_strategy
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
        },
        "EMA_RSI_V1": {
            "name": "Bias Buy/Sell (EMA + RSI)",
            "description": "Trend Following (EMA200) with Counter-Trend Entry (RSI)",
            "defaults": {
                "ema_period": 200,
                "rsi_period": 14,
                "rsi_overbought": 70,
                "rsi_oversold": 30
            }
        }
    }

    @classmethod
    def get_strategy(cls, template_id: str):
        return cls._strategies.get(template_id)

    @classmethod
    def get_strategy_logic(cls, template_id: str):
        return cls._strategies.get(template_id)

    @classmethod
    def get_metadata(cls, template_id: str):
        return cls._metadata.get(template_id)

    @classmethod
    def list_templates(cls):
        return [{"id": k, **v} for k, v in cls._metadata.items()]

    @classmethod
    def register_custom(cls, template_id: str, code: str, name: str = "Custom Strategy"):
        """
        Dynamically compiles and registers a user-defined strategy.
        WARNING: exec() is used. Ensure code is sandboxed or trusted in production.
        """
        try:
            # 1. Prepare Globals
            # We allow basic imports and app modules
            allowed_globals = {
                "pd": pd,
                "check_macro_bias": check_macro_bias,
                "check_setup_zone": check_setup_zone,
                "check_trigger": check_trigger,
                "calculate_stop_loss": calculate_stop_loss,
                "calculate_ema": calculate_ema,
                "calculate_rsi": calculate_rsi,
                "calculate_macd": calculate_macd,
                "SignalDirection": SignalDirection,
                "logger": logger
            }
            
            # 2. Compile
            local_scope = {}
            exec(code, allowed_globals, local_scope)
            
            # 3. Extract Function
            if "strategy" not in local_scope:
                raise ValueError("Code must define an async function named 'strategy(state, data_manager)'")
            
            func = local_scope["strategy"]
            if not asyncio.iscoroutinefunction(func):
                 raise ValueError("'strategy' function must be async")

            # 4. Register
            cls._strategies[template_id] = func
            cls._metadata[template_id] = {
                "name": name,
                "description": "User defined custom strategy",
                "defaults": {}
            }
            logger.info(f"Registered custom strategy {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to compile custom strategy {template_id}: {e}")
            raise e


