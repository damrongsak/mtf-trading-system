import logging
import pandas as pd
from app.indicators import calculate_macd

logger = logging.getLogger(__name__)

METADATA = {
    "name": "MACD Crossover",
    "description": "Standard Momentum Strategy",
    "defaults": {}
}

async def strategy(state, data_manager):
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
        
        # Bullish Crossover
        if prev_macd < prev_sig and curr_macd > curr_sig:
            direction = "BULLISH"
            reason = f"MACD Bullish Crossover (MACD {curr_macd:.4f} > Sig {curr_sig:.4f})"
        
        # Bearish Crossover
        elif prev_macd > prev_sig and curr_macd < curr_sig:
             direction = "BEARISH"
             reason = f"MACD Bearish Crossover (MACD {curr_macd:.4f} < Sig {curr_sig:.4f})"
             
        if direction:
             sl_price = df['low'].iloc[-5:].min() if direction == "BULLISH" else df['high'].iloc[-5:].max()
             
             return {
                "direction": direction,
                "stop_loss": sl_price,
                "reason": reason,
                "metadata": {
                    "signal_timestamp": str(df.index[-1]),
                    "macd": float(curr_macd),
                    "signal": float(curr_sig)
                }
            }
            
    except Exception as e:
        logger.error(f"Error in MACD Strategy for {symbol}: {e}")
        return None
        
    return None
