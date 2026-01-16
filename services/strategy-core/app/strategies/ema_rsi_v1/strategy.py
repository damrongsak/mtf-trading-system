import logging
import pandas as pd
from app.indicators import calculate_ema, calculate_rsi

logger = logging.getLogger(__name__)

async def strategy(state, data_manager):
    """
    EMA (200) + RSI (14) Strategy
    - Bullish: Price > EMA and RSI < 30 (Oversold -> Buy Dip)
    - Bearish: Price < EMA and RSI > 70 (Overbought -> Sell Rally)
    """
    symbol = state.symbol
    config = state.config_json if hasattr(state, 'config_json') else {}
    ema_period = config.get('ema_period', 200)
    rsi_period = config.get('rsi_period', 14)
    rsi_overbought = config.get('rsi_overbought', 70)
    rsi_oversold = config.get('rsi_oversold', 30)
    
    df = data_manager.get_data(symbol)
    if df.empty or len(df) < ema_period + 10:
        return None
        
    try:
        close = df['close']
        
        # Calculate EMA
        ema = calculate_ema(close, span=ema_period)
        
        # Calculate RSI
        rsi = calculate_rsi(close, window=rsi_period)
        
        current_price = close.iloc[-1]
        current_ema = ema.iloc[-1]
        current_rsi = rsi.iloc[-1]
        
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
                "reason": reason,
                "metadata": {
                    "signal_timestamp": str(df.index[-1]),
                    "ema": float(current_ema),
                    "rsi": float(current_rsi)
                }
            }
            
    except Exception as e:
        logger.error(f"Error in EMA_RSI strategy for {symbol}: {e}")
        return None
        
    return None
