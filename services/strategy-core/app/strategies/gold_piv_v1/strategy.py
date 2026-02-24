import logging
import pandas as pd
import numpy as np
from app.indicators.volatility import calculate_yang_zhang
from app.indicators.trend import calculate_ema
from app.indicators.piv import calculate_n_bands, calculate_piv_levels, calculate_true_slope
from app.indicators.garch_engine import garch_engine
from app.logic import SignalDirection

logger = logging.getLogger(__name__)

METADATA = {
    "name": "Gold PIV Structural Strategy",
    "description": "Strategy for XAU/USD using Projected Implied Volatility (PIV) and GJR-GARCH.",
    "version": "1.0",
    "author": "Antigravity",
    "defaults": {
        "tf_trigger": "15min",
        "tf_setup": "1h",
        "multiplier": 2.0,
        "piv_prominence": 0.5
    }
}

async def strategy(state, data_manager):
    """
    Gold PIV Strategy:
    - Setup: Projected Volatility (GARCH/GVZ) + N-Bands Confluence
    - Trigger: True Slope reversal at extremes
    - Filter: H1 Bias (EMA 200)
    """
    # Prefer config_json if available (standard in this system)
    params = getattr(state, "config_json", {}) or METADATA["defaults"]
    
    symbol = state.symbol
    tf_trigger = params.get("tf_trigger", "15min")
    tf_setup = params.get("tf_setup", "1h")
    
    # 1. Fetch Data
    try:
        # M15 for Trigger logic
        df_trigger = data_manager.get_candles(symbol, timeframe=tf_trigger, limit=500)
        # H1 for Context & GARCH
        df_setup = data_manager.get_candles(symbol, timeframe=tf_setup, limit=250) # Increased for EMA 200
        
        if df_trigger.empty or df_setup.empty or len(df_trigger) < 50 or len(df_setup) < 200:
            return None
            
    except Exception as e:
        logger.warning(f"Data fetch failed for {symbol} in Gold PIV: {e}")
        return None

    # Performance Optimization: Skip if we've already processed this candle
    current_idx_trigger = df_trigger.index[-1]
    last_idx = state.state.get("last_processed_idx")
    if last_idx == current_idx_trigger:
        return None
    state.state["last_processed_idx"] = current_idx_trigger

    # 2. Volatility Analysis
    # Optimization: Cache GARCH result for the current H1 candle
    current_idx_setup = df_setup.index[-1]
    cached_vol = state.state.get("cached_projected_vol")
    cached_setup_idx = state.state.get("last_setup_idx")

    if cached_vol is not None and cached_setup_idx == current_idx_setup:
        projected_vol = cached_vol
    else:
        h1_returns = df_setup['close'].pct_change().dropna()
        projected_vol = garch_engine.get_projected_volatility(h1_returns)
        state.state["cached_projected_vol"] = projected_vol
        state.state["last_setup_idx"] = current_idx_setup
    
    # Intraday Precision Volatility (Yang-Zhang)
    yz_vol = calculate_yang_zhang(df_trigger['open'], df_trigger['high'], df_trigger['low'], df_trigger['close'])
    current_yz = yz_vol.iloc[-1]
    
    # 3. Macro Bias (H1 EMA 200)
    ema_200 = calculate_ema(df_setup['close'], span=200)
    current_price = df_trigger['close'].iloc[-1]
    
    # Bias is based on setup timeframe
    bias = SignalDirection.LONG if current_price > ema_200.iloc[-1] else SignalDirection.SHORT
    
    # 4. PIV Structure (N-Bands)
    from app.indicators.volatility import calculate_atr
    atr_trigger = calculate_atr(df_trigger['high'], df_trigger['low'], df_trigger['close'])
    
    multiplier = params.get("multiplier", 2.0)
    bands = calculate_n_bands(df_trigger['close'], atr_trigger, projected_vol, multipliers=[multiplier])
    
    # 5. Trading Triggers (True Slope)
    slope = calculate_true_slope(df_trigger['close'])
    current_slope = slope.iloc[-1]
    prev_slope = slope.iloc[-2]
    
    signal = None
    
    # Bullish Case: Bias Long + Price at/below Lower Band + Slope reversal
    if bias == SignalDirection.LONG:
        lower_band = bands[f'n_band_lower_{multiplier}'].iloc[-1]
        if current_price <= lower_band:
            if prev_slope < 0 and current_slope > 0:
                signal = {
                    "direction": "BULLISH",
                    "price": float(current_price),
                    "stop_loss": float(df_trigger['low'].iloc[-5:].min()),
                    "reason": f"Gold PIV Reversal: Lower Band + Pos Slope (GARCH/GVZ: {projected_vol:.1f})",
                    "confidence": 0.8,
                    "meta_data": {
                        "projected_vol": float(projected_vol),
                        "yz_vol": float(current_yz),
                        "multiplier": multiplier,
                        "slope": float(current_slope)
                    }
                }
                
    # Bearish Case: Bias Short + Price at/above Upper Band + Slope reversal
    elif bias == SignalDirection.SHORT:
        upper_band = bands[f'n_band_upper_{multiplier}'].iloc[-1]
        if current_price >= upper_band:
            if prev_slope > 0 and current_slope < 0:
                signal = {
                    "direction": "BEARISH",
                    "price": float(current_price),
                    "stop_loss": float(df_trigger['high'].iloc[-5:].max()),
                    "reason": f"Gold PIV Reversal: Upper Band + Neg Slope (GARCH/GVZ: {projected_vol:.1f})",
                    "confidence": 0.8,
                    "meta_data": {
                        "projected_vol": float(projected_vol),
                        "yz_vol": float(current_yz),
                        "multiplier": multiplier,
                        "slope": float(current_slope)
                    }
                }

    if signal:
        logger.info(f"PIV SIGNAL: {symbol} {signal['direction']} at {signal['price']}")

    return signal
