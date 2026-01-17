
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


def strategy(data, params=None):
    """
    Unified Strategy: Volatility Compression Breakout
    """
    if params is None:
        params = {}
        
    config = METADATA["defaults"].copy()
    config.update(params)
    
    # Parameters
    atr_period = int(config.get('atr_period', 14))
    atr_smooth_period = int(config.get('atr_smooth_period', 20))
    adr_period = int(config.get('adr_period', 20))
    keltner_mult = float(config.get('keltner_mult', 2.0))
    
    if data.empty or len(data) < max(atr_period, adr_period) + 20:
        return None, None, None
        
    try:
        high = data['high']
        low = data['low']
        close = data['close']
        
        # 1. Indicators
        atr = calculate_atr(high, low, close, window=atr_period)
        atr_sma = atr.rolling(window=atr_smooth_period).mean()
        
        adr = calculate_adr(high, low, window=adr_period)
        emax = calculate_ema(close, span=20) # Keltner Center
        
        # 2. Vectorized Logic
        # Compression: Current Vol (ATR) < Average Vol (ATR SMA)
        compression = (atr < atr_sma)
        
        # "Was in Compression" = Previous bar was compressed
        was_compression = compression.shift(1)
        
        # Keltner Channels
        upper_channel = emax + (keltner_mult * atr)
        lower_channel = emax - (keltner_mult * atr)
        
        # Breakout
        breakout_up = close > upper_channel
        breakout_down = close < lower_channel
        
        # Signal = Was in Compression AND Breaking out now
        # Note: We trigger on the FIRST bar of breakout
        entries = was_compression & breakout_up
        exits = was_compression & breakout_down
        
        # 3. Live Context (Last Candle)
        current_close = close.iloc[-1]
        curr_upper = upper_channel.iloc[-1]
        curr_lower = lower_channel.iloc[-1]
        current_atr = atr.iloc[-1]
        current_atr_sma = atr_sma.iloc[-1]
        current_adr = adr.iloc[-1]
        
        compression_ratio = current_atr / current_atr_sma if current_atr_sma > 0 else 1.0
        
        direction = None
        reason = ""
        
        if entries.iloc[-1]:
            direction = "BULLISH"
            reason = f"Volatility Breakout Up (Close {current_close:.2f} > Upper {curr_upper:.2f})"
        elif exits.iloc[-1]:
            direction = "BEARISH"
            reason = f"Volatility Breakout Down (Close {current_close:.2f} < Lower {curr_lower:.2f})"
        
        signal_dict = None
        if direction:
            # Stop Loss: 2 * ATR
            sl_dist = 2.0 * current_atr
            stop_loss = current_close - sl_dist if direction == "BULLISH" else current_close + sl_dist
            
            # Target: 1 * ADR (Daily Range expansion target)
            tp_dist = current_adr
            target_price = current_close + tp_dist if direction == "BULLISH" else current_close - tp_dist
            
            # AI Metadata
            metadata = {
                "signal_timestamp": str(data.index[-1]),
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
            
            signal_dict = {
                "direction": direction,
                "stop_loss": stop_loss,
                "target_price": target_price,
                "reason": reason,
                "metadata": metadata
            }
            
        return entries, exits, signal_dict
            
    except Exception as e:
        logger.error(f"Error in Volatility Breakout Strategy: {e}")
        return None, None, None
