import logging
import pandas as pd
from app.indicators import calculate_macd

logger = logging.getLogger(__name__)

METADATA = {
    "name": "MACD Crossover",
    "description": "Standard Momentum Strategy",
    "defaults": {}
}


def strategy(data, params=None):
    """
    Unified Strategy: MACD Crossover
    Args:
        data: pd.DataFrame
        params: dict
    """
    if params is None:
        params = {}
        
    config = METADATA["defaults"].copy()
    config.update(params)
    
    fast = int(config.get('fast', 12))
    slow = int(config.get('slow', 26))
    signal_period = int(config.get('signal', 9))
    
    if data.empty or len(data) < slow + signal_period + 10:
        return None, None, None
        
    try:
        close = data['close']
        
        # 1. Indicators
        macd_ind = calculate_macd(close, fast=fast, slow=slow, signal=signal_period)
        
        macd_line = macd_ind.macd
        signal_line = macd_ind.signal
        
        # 2. Vectorized Logic
        # Crossover: Current > Signal AND Previous <= Previous Signal
        crossover = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
        crossunder = (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))
        
        entries = crossover
        exits = crossunder
        
        # 3. Live Context (Last Candle)
        curr_macd = macd_line.iloc[-1]
        curr_sig = signal_line.iloc[-1]
        
        direction = None
        reason = ""
        
        if entries.iloc[-1]:
            direction = "BULLISH"
            reason = f"MACD Bullish Crossover (MACD {curr_macd:.4f} > Sig {curr_sig:.4f})"
        
        elif exits.iloc[-1]:
             direction = "BEARISH"
             reason = f"MACD Bearish Crossover (MACD {curr_macd:.4f} < Sig {curr_sig:.4f})"
             
        signal_dict = None
        if direction:
             sl_price = data['low'].iloc[-5:].min() if direction == "BULLISH" else data['high'].iloc[-5:].max()
             
             signal_dict = {
                "direction": direction,
                "stop_loss": sl_price,
                "reason": reason,
                "metadata": {
                    "signal_timestamp": str(data.index[-1]),
                    "macd": float(curr_macd),
                    "signal": float(curr_sig)
                }
            }
            
        return entries, exits, signal_dict
            
    except Exception as e:
        logger.error(f"Error in MACD Strategy: {e}")
        return None, None, None
