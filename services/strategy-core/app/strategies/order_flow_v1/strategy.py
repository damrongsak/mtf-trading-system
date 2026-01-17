
import vectorbt as vbt
import pandas as pd
import numpy as np
from app.indicators.orderflow import detect_imbalance, is_absorption

METADATA = {
    "name": "Order Flow V1",
    "description": "Momentum strategy based on Footprint Imbalance and Price Action.",
    "defaults": {
        "ema_period": 200,
        "imbalance_ratio": 3.0,
        "sl_pips": 20.0,
        "tp_pips": 40.0
    }
}

def strategy(data: pd.DataFrame, params: dict = None):
    """
    Order Flow Strategy (Sync/Vectorized hybrid)
    Args:
        data: pd.DataFrame (ohlcv + footprint + delta)
        params: dict of parameters
    Returns:
        entries, exits, signal_dict
    """
    if params is None: params = {}
    ema_period = int(params.get("ema_period", METADATA["defaults"]["ema_period"]))
    ratio = float(params.get("imbalance_ratio", METADATA["defaults"]["imbalance_ratio"]))
    sl_pips = float(params.get("sl_pips", METADATA["defaults"]["sl_pips"]))
    
    close = data['close']
    high = data['high']
    low = data['low']
    
    # 1. Macro Filter: Price > EMA(200)
    ema = vbt.MA.run(close, ema_period)
    trend_filter = close > ema.ma
    
    # 2. Imbalance Detection (Non-Vectorized Loop for now due to JSON structure)
    # Ideally should be optimized, but for MVP we iterate
    imbalance_signal = pd.Series(False, index=close.index)
    
    # Check if 'footprint' column exists (it might not in early testing)
    if 'footprint' in data.columns:
        # We look for imbalance in the *current* or *recent* candles
        # Using apply is slow but functional
        def has_imbalance(row):
            # Mock candle dict for our indicator function
            candle_dict = {
                'footprint': row.get('footprint'),
                'open': row['open'], 'close': row['close'],
                'high': row['high'], 'low': row['low'],
                'volume': row['volume']
            }
            levels = detect_imbalance(candle_dict, ratio)
            return len(levels) > 0

        imbalance_signal = data.apply(has_imbalance, axis=1)
        
    # 3. Pullback / Absorption Logic
    # Simple proxy: If we had an imbalance recently, and now we have a pullback
    # For MVP: Entry on Candle Close if Imbalance Detected AND Trend Filter OK
    # Real logic requiring "Wait for Pullback" is complex for vectorbt standard signal generation
    # without a state machine. We will implement the "Breakout" scenario here:
    # Aggressive Buy on Imbalance Candle.
    
    entries = trend_filter & imbalance_signal
    exits = pd.Series(False, index=entries.index) # No fixed exit signal, use SL/TP
    
    # 4. Construct Signal Dict
    latest_signal = {
        "direction": "BULLISH" if entries.iloc[-1] else "NEUTRAL",
        "stop_loss": float(close.iloc[-1] - (sl_pips * 0.0001)), # Rough Approx
        "take_profit": float(close.iloc[-1] + (params.get("tp_pips", 40) * 0.0001)),
        "reason": "Imbalance + Trend",
        "metadata": {
            "strategy_name": METADATA["name"],
            "trend_ok": bool(trend_filter.iloc[-1]),
            "imbalance_detected": bool(imbalance_signal.iloc[-1])
        }
    }
    
    return entries, exits, latest_signal
