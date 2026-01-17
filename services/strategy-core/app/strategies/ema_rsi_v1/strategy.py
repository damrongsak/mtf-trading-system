import logging
import pandas as pd
from app.indicators import calculate_ema, calculate_rsi

logger = logging.getLogger(__name__)

METADATA = {
    "name": "Bias Buy/Sell (EMA + RSI)",
    "description": "Trend Following (EMA200) with Counter-Trend Entry (RSI)",
    "defaults": {
        "ema_period": 200,
        "rsi_period": 14,
        "rsi_overbought": 70,
        "rsi_oversold": 30
    }
}


def strategy(data, params=None):
    """
    Unified Strategy: EMA (200) + RSI (14)
    Args:
        data: pd.DataFrame
        params: dict
    """
    if params is None:
        params = {}
        
    # Load Config
    defaults = METADATA["defaults"]
    ema_period = int(params.get('ema_period', defaults['ema_period']))
    rsi_period = int(params.get('rsi_period', defaults['rsi_period']))
    rsi_overbought = int(params.get('rsi_overbought', defaults['rsi_overbought']))
    rsi_oversold = int(params.get('rsi_oversold', defaults['rsi_oversold']))
    
    if data.empty or len(data) < ema_period + 10:
        return None, None, None
        
    try:
        close = data['close']
        
        # 1. Indicators
        ema = calculate_ema(close, span=ema_period)
        rsi = calculate_rsi(close, window=rsi_period)
        
        # 2. Vectorized Logic
        is_uptrend = close > ema
        is_downtrend = close < ema
        
        # Bullish Signal: Uptrend + RSI Oversold
        entries = is_uptrend & (rsi < rsi_oversold)
        
        # Bearish Signal: Downtrend + RSI Overbought
        # Mapping this to 'exits' for now, or if Shorting is allowed, logic might need 'short_entries'.
        # Assuming entries/exits logic:
        # Exits = Bearish Trigger (Sell Rally)
        exits = is_downtrend & (rsi > rsi_overbought)
        
        # 3. Live Context (Last Candle)
        current_price = close.iloc[-1]
        current_ema = ema.iloc[-1]
        current_rsi = rsi.iloc[-1]
        
        direction = None
        reason = ""
        
        if entries.iloc[-1]:
            direction = "BULLISH"
            reason = f"Uptrend (Price {current_price:.2f} > EMA {current_ema:.2f}) + RSI Oversold ({current_rsi:.2f})"
        elif exits.iloc[-1]:
            direction = "BEARISH"
            reason = f"Downtrend (Price {current_price:.2f} < EMA {current_ema:.2f}) + RSI Overbought ({current_rsi:.2f})"
            
        signal_dict = None
        if direction:
             signal_dict = {
                "direction": direction,
                "stop_loss": float(current_ema), # Simple SL at EMA
                "reason": reason,
                "metadata": {
                    "signal_timestamp": str(data.index[-1]),
                    "ema": float(current_ema),
                    "rsi": float(current_rsi)
                }
            }
            
        return entries, exits, signal_dict
            
    except Exception as e:
        logger.error(f"Error in EMA_RSI strategy: {e}")
        return None, None, None
