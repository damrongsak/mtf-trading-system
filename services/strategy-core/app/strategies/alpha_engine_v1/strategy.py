import logging
import pandas as pd
from app.engine.expression_engine import ExpressionEngine
from app.indicators import calculate_atr

logger = logging.getLogger(__name__)

METADATA = {
    "name": "Athena Alpha Engine",
    "description": "Generic Formula Execution",
    "defaults": {
        "formula": "rsi(close, 14)",
        "threshold_long": 30,
        "condition_long": "lt",
        "threshold_short": 70,
        "condition_short": "gt"
    }
}

async def strategy(state, data_manager):
    """
    ALPHA_ENGINE_V1: Generic Formula Execution.
    Config:
        - formula: "rsi(close, 14)"
        - threshold_long: 30
        - threshold_short: 70
    """
    symbol = state.symbol
    config = state.config_json if hasattr(state, 'config_json') else {}
    formula = config.get('formula')
    threshold_long = config.get('threshold_long')
    threshold_short = config.get('threshold_short')
    
    if not formula:
        return None
        
    df = data_manager.get_data(symbol)
    if df.empty:
        return None
        
    engine = ExpressionEngine()
    try:
        context = {col: df[col] for col in df.columns}
        result_series = engine.evaluate(formula, context)
        
        if isinstance(result_series, (float, int)):
            current_val = result_series
        else:
             current_val = result_series.iloc[-1]
             
        direction = None
        reason = ""
        
        cond_long = config.get('condition_long', 'gt')
        cond_short = config.get('condition_short', 'lt')
        
        # Check Long
        if threshold_long is not None:
            hit = False
            if cond_long == 'gt' and current_val > threshold_long: hit = True
            elif cond_long == 'lt' and current_val < threshold_long: hit = True
            
            if hit:
                direction = "BULLISH"
                reason = f"Alpha ({formula}) {current_val:.2f} check {cond_long} {threshold_long}"

        # Check Short
        if threshold_short is not None and not direction:
            hit = False
            if cond_short == 'gt' and current_val > threshold_short: hit = True
            elif cond_short == 'lt' and current_val < threshold_short: hit = True
            
            if hit:
                direction = "BEARISH"
                reason = f"Alpha ({formula}) {current_val:.2f} check {cond_short} {threshold_short}"
                
        if direction:
            atr_series = calculate_atr(df['high'], df['low'], df['close'], 14)
            current_atr = atr_series.iloc[-1]
            current_close = df['close'].iloc[-1]
            
            sl_price = current_close - (2.0 * current_atr) if direction == "BULLISH" else current_close + (2.0 * current_atr)
            
            return {
                "direction": direction,
                "stop_loss": sl_price,
                "reason": reason,
                "metadata": {
                    "signal_timestamp": str(df.index[-1]),
                    "alpha_score": float(current_val)
                }
            }
            
    except Exception as e:
        logger.error(f"Alpha Engine Error {symbol}: {e}")
        return None
        
    return None
