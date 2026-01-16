
import logging
import pandas as pd
import numpy as np
from app.indicators.volatility import calculate_atr, calculate_adr
from app.indicators import calculate_ema

logger = logging.getLogger(__name__)

METADATA = {
    "name": "Volatility Breakout V1",
    "description": "Compression Breakout Strategy with AI Metadata",
    "defaults": {
        "atr_period": 14,
        "atr_smooth_period": 20,
        "adr_period": 20,
        "keltner_mult": 2.0
    }
}

async def strategy(state, data_manager):
    """
    STRAT_VOL_BREAKOUT_V1: Volatility Compression Breakout Strategy
    
    Logic:
    1. Identify Compression: 
       - Current ATR(14) < SMA(ATR(14), 20) 
       - OR Current Daily Range < ADR(20)
    2. Identify Breakout:
       - Price closes outside Keltner Channels (EMA +/- 2*ATR)
    3. Signal:
       - Buy if Close > Upper Channel
       - Sell if Close < Lower Channel
    4. AI Context:
       - Metadata includes compression ratios and regimes.
    """
    symbol = state.symbol
    config = state.config_json if hasattr(state, 'config_json') else {}
    
    # Parameters
    atr_period = config.get('atr_period', 14)
    atr_smooth_period = config.get('atr_smooth_period', 20)
    adr_period = config.get('adr_period', 20)
    keltner_mult = config.get('keltner_mult', 2.0)
    
    # 1. Get Data
    df = data_manager.get_data(symbol)
    if df.empty or len(df) < max(atr_period, adr_period) + 20:
        return None
        
    try:
        high = df['high']
        low = df['low']
        close = df['close']
        
        # 2. Indicators
        atr = calculate_atr(high, low, close, window=atr_period)
        atr_sma = atr.rolling(window=atr_smooth_period).mean()
        
        adr = calculate_adr(high, low, window=adr_period)
        
        ema = calculate_ema(close, span=20) # Keltner Center
        
        current_atr = atr.iloc[-1]
        current_atr_sma = atr_sma.iloc[-1]
        current_adr = adr.iloc[-1]
        
        # Current daily range (Need to estimate if intraday, or use previous day)
        # For simplicity, using (High - Low) of current bar as proxy for "volatility now" vs daily avg?
        # No, the spec says "Period of low volatility". 
        # Let's use the ATR Ratio.
        
        compression_ratio = current_atr / current_atr_sma if current_atr_sma > 0 else 1.0
        
        # Check Compression (Regime)
        is_compression = compression_ratio < 1.0
        
        # Keltner Channels
        upper_channel = ema + (keltner_mult * atr)
        lower_channel = ema - (keltner_mult * atr)
        
        current_close = close.iloc[-1]
        prev_close = close.iloc[-2]
        
        curr_upper = upper_channel.iloc[-1]
        curr_lower = lower_channel.iloc[-1]
        
        # 3. Logic: Breakout from Compression
        direction = None
        reason = ""
        
        # We want to have BEEN in compression, and now BREAKING OUT.
        # Or simply: Logic is "Breakout", and we tag metadata with regim?
        # Spec says: "Context: Market is in BLOCK_VOL_COMPRESSION".
        # So we trigger ONLY if we observe compression recently.
        # Let's check if we were in compression 1 bar ago.
        
        prev_atr = atr.iloc[-2]
        prev_atr_sma = atr_sma.iloc[-2]
        was_compression = prev_atr < prev_atr_sma
        
        if was_compression:
            # Check Breakout
            if current_close > curr_upper:
                direction = "BULLISH"
                reason = f"Volatility Breakout Up (Close {current_close:.2f} > Upper {curr_upper:.2f})"
            elif current_close < curr_lower:
                direction = "BEARISH"
                reason = f"Volatility Breakout Down (Close {current_close:.2f} < Lower {curr_lower:.2f})"
        
        if direction:
            # Stop Loss: 2 * ATR
            sl_dist = 2.0 * current_atr
            stop_loss = current_close - sl_dist if direction == "BULLISH" else current_close + sl_dist
            
            # Target: 1 * ADR (Daily Range expansion target)
            tp_dist = current_adr
            target_price = current_close + tp_dist if direction == "BULLISH" else current_close - tp_dist
            
            # AI Metadata
            metadata = {
                "signal_timestamp": str(df.index[-1]), # Explicit candle time
                "volatility": {
                    "atr_14": float(current_atr),
                    "adr_20": float(current_adr),
                    "compression_ratio": float(compression_ratio),
                    "regime": "EXPANSION (Exiting Compression)"
                },
                "technical": {
                    "breakout_level": float(current_close),
                    "keltner_upper": float(curr_upper),
                    "keltner_lower": float(curr_lower)
                }
            }
            
            return {
                "direction": direction,
                "stop_loss": stop_loss,
                "target_price": target_price,
                "reason": reason,
                "metadata": metadata
            }
            
    except Exception as e:
        logger.error(f"Error in Volatility Breakout Strategy {symbol}: {e}")
        return None
        
    return None
