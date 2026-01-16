import logging
import pandas as pd
from app.engine.expression_engine import ExpressionEngine
from app.indicators.smc import detect_order_blocks

logger = logging.getLogger(__name__)

async def strategy(state, data_manager):
    """
    HYBRID_ALPHA_V1: Setup (Alpha/Momentum) + Trigger (SMC/OrderBlock).
    """
    symbol = state.symbol
    config = state.config_json if hasattr(state, 'config_json') else {}
    alpha_threshold = config.get('alpha_threshold', 0.8)
    
    formula = "ts_rank(close / delay(close, 10), 20)" 
    
    df = data_manager.get_data(symbol)
    if df.empty or len(df) < 50: return None
    
    engine = ExpressionEngine()
    try:
        context = {col: df[col] for col in df.columns}
        alpha_series = engine.evaluate(formula, context)
        current_alpha = alpha_series.iloc[-1]
        
        if current_alpha < alpha_threshold:
            return None # Filtered
            
        obs = detect_order_blocks(df)
        current_close = df['close'].iloc[-1]
        
        valid_ob = None
        for ob in obs:
            if ob['type'] == 'bullish' and ob['mitigated'] == False:
                 if current_close > ob['top'] and (current_close - ob['top']) / current_close < 0.005: 
                      valid_ob = ob
                      break
        
        if valid_ob:
             sl_price = valid_ob['bottom']
             
             return {
                 "direction": "BULLISH",
                 "stop_loss": sl_price,
                 "reason": f"Hybrid: High Momentum ({current_alpha:.2f}) + Bouncing off OB",
                 "metadata": {
                     "signal_timestamp": str(df.index[-1]),
                     "alpha_score": float(current_alpha),
                     "ob_index": valid_ob['index']
                 }
             }

    except Exception as e:
        logger.error(f"Hybrid Strategy Error {symbol}: {e}")
        return None
        
    return None
