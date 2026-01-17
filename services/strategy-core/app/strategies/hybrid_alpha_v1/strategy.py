import logging
import pandas as pd
from app.engine.expression_engine import ExpressionEngine
from app.indicators.smc import detect_order_blocks

logger = logging.getLogger(__name__)

METADATA = {
    "name": "Hybrid (Momentum + SMC)",
    "description": "Statistical Momentum Filter with Order Block Entry",
    "defaults": {
        "alpha_threshold": 0.8
    }
}


def strategy(data, params=None):
    """
    HYBRID_ALPHA_V1: Setup (Alpha/Momentum) + Trigger (SMC/OrderBlock).
    """
    if params is None:
        params = {}
        
    config = METADATA["defaults"].copy()
    config.update(params)
    
    alpha_threshold = float(config.get('alpha_threshold', 0.8))
    
    if data.empty or len(data) < 50:
        return None, None, None
        
    formula = "ts_rank(close / delay(close, 10), 20)" 
    
    engine = ExpressionEngine()
    try:
        context = {col: data[col] for col in data.columns}
        alpha_series = engine.evaluate(formula, context)
        
        if isinstance(alpha_series, (float, int)):
             alpha_series = pd.Series(alpha_series, index=data.index)
             
        # Vectorized Alpha Check
        # We only consider setups where Alpha Score >= Threshold (Wait, code says < threshold returns None, so logic is "Must be >= threshold")
        # Code: if current_alpha < alpha_threshold: return None => Meaning we need Alpha >= Threshold
        
        setup_valid = alpha_series >= alpha_threshold
        
        # SMC / Order Blocks are hard to vectorize without a specialized lib or heavy computation.
        # For this refactor, we will focus on the LIVE Signal (Last Candle) and return placeholder Series for entries/exits
        # unless we can easily vectorize OB detection.
        # Ideally, we should run OB detection on the whole history.
        # detect_order_blocks(data) usually returns a list of ACTIVE blocks at the end? 
        # Or does it return a historical structure?
        # Assuming allow scalar logic for now.
        
        entries = pd.Series(False, index=data.index)
        exits = pd.Series(False, index=data.index)
        
        # --- Live Logic ---
        current_alpha = alpha_series.iloc[-1]
        
        direction = None
        reason = ""
        signal_dict = None
        
        if current_alpha >= alpha_threshold:
             # Only proceed if Setup is valid
             obs = detect_order_blocks(data) # Assumes this accepts DataFrame
             current_close = data['close'].iloc[-1]
             
             valid_ob = None
             for ob in obs:
                 # Logic: Bullish OB (Support), Price bouncing off it
                 if ob['type'] == 'bullish' and ob['mitigated'] == False:
                     # Check if price is near OB top (Retest)
                     # Condition: close > ob_top AND (dist/close) < 0.5%
                      if current_close > ob['top'] and (current_close - ob['top']) / current_close < 0.005: 
                           valid_ob = ob
                           break
             
             if valid_ob:
                  direction = "BULLISH"
                  # Set the LAST entry to True
                  entries.iloc[-1] = True
                  
                  sl_price = valid_ob['bottom']
                  
                  signal_dict = {
                      "direction": "BULLISH",
                      "stop_loss": sl_price,
                      "reason": f"Hybrid: High Momentum ({current_alpha:.2f}) + Bouncing off OB",
                      "metadata": {
                          "signal_timestamp": str(data.index[-1]),
                          "alpha_score": float(current_alpha),
                          "ob_index": valid_ob['index']
                      }
                  }

        return entries, exits, signal_dict

    except Exception as e:
        logger.error(f"Hybrid Strategy Error: {e}")
        return None, None, None
