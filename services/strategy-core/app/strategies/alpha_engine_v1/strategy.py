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


def strategy(data, params=None):
    """
    ALPHA_ENGINE_V1: Generic Formula Execution.
    Config:
        - formula: "rsi(close, 14)"
        - threshold_long: 30
        - threshold_short: 70
    """
    if params is None:
        params = {}
        
    # Use defaults if not provided
    config = METADATA["defaults"].copy()
    config.update(params)
    
    formula = config.get('formula')
    threshold_long = config.get('threshold_long')
    threshold_short = config.get('threshold_short')
    
    if data.empty or not formula:
        return None, None, None
        
    engine = ExpressionEngine()
    try:
        # Context for Expression Engine (using Vectorized Series)
        context = {col: data[col] for col in data.columns}
        result_series = engine.evaluate(formula, context)
        
        # Ensure result is a Series for vectorization
        if isinstance(result_series, (float, int)):
            # Broadcast to series
            result_series = pd.Series(result_series, index=data.index)
            
        # --- 1. Vectorized Signals ---
        cond_long = config.get('condition_long', 'gt')
        cond_short = config.get('condition_short', 'lt')
        
        entries = pd.Series(False, index=data.index)
        exits = pd.Series(False, index=data.index)
        
        # Long Logic
        if threshold_long is not None:
            if cond_long == 'gt':
                entries = result_series > threshold_long
            elif cond_long == 'lt':
                entries = result_series < threshold_long
                
        # Short Logic (if separate exits are needed, otherwise 'exits' might be purely SL/TP)
        # Or if this engine supports Short Entries?
        # The original code had "Check Long" and "Check Short".
        # Assuming "Check Short" means "Enter Short" (BEARISH).
        # We'll map "Bearish" signals to 'exits' for now, or distinct 'short_entries' if architecture supported it.
        # But standard return is (entries, exits, signal).
        # Let's assume 'entries' = LONG, 'exits' = SHORT/CLOSE.
        
        if threshold_short is not None:
             if cond_short == 'gt':
                 exits = result_series > threshold_short
             elif cond_short == 'lt':
                 exits = result_series < threshold_short
        
        # --- 2. Live Signal (Last Candle) ---
        current_val = result_series.iloc[-1]
        direction = None
        reason = ""
        
        if entries.iloc[-1]:
            direction = "BULLISH"
            reason = f"Alpha ({formula}) {current_val:.2f} check {cond_long} {threshold_long}"
        elif exits.iloc[-1]: # If Short signal
            direction = "BEARISH"
            reason = f"Alpha ({formula}) {current_val:.2f} check {cond_short} {threshold_short}"
            
        signal_dict = None
        if direction:
            atr_series = calculate_atr(data['high'], data['low'], data['close'], 14)
            current_atr = atr_series.iloc[-1]
            current_close = data['close'].iloc[-1]
            
            sl_price = current_close - (2.0 * current_atr) if direction == "BULLISH" else current_close + (2.0 * current_atr)
            
            signal_dict = {
                "direction": direction,
                "stop_loss": sl_price,
                "reason": reason,
                "metadata": {
                    "signal_timestamp": str(data.index[-1]),
                    "alpha_score": float(current_val)
                }
            }
            
        return entries, exits, signal_dict
            
    except Exception as e:
        logger.error(f"Alpha Engine Error: {e}")
        return None, None, None
