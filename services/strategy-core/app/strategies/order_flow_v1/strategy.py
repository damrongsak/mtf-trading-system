
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

def _calculate_imbalance_series(data: pd.DataFrame, ratio: float) -> pd.Series:
    """Helper to detect imbalance across the DataFrame rows."""
    if 'footprint' not in data.columns:
        return pd.Series(False, index=data.index)
        
    def has_imbalance(row):
        # Construct candle dict for indicator function
        # Using row.get() safely
        candle_dict = {
            'footprint': row.get('footprint'),
            'open': row.get('open'), 
            'close': row.get('close'),
            'high': row.get('high'), 
            'low': row.get('low'),
            'volume': row.get('volume')
        }
        levels = detect_imbalance(candle_dict, ratio)
        return len(levels) > 0

    return data.apply(has_imbalance, axis=1)

def strategy(data: pd.DataFrame, params: dict = None):
    """
    Order Flow Strategy (Sync/Vectorized hybrid)
    
    Logic:
    1. Filter: Price above EMA(200)
    2. Trigger: Aggressive Imbalance detected in Footprint
    3. Exit: Fixed SL/TP (managed by Execution Service / Signal Dict)
    
    Args:
        data: pd.DataFrame (ohlcv + footprint + delta)
        params: dict of parameters
        
    Returns:
        entries, exits, signal_dict
    """
    if params is None: params = {}
    
    # 0. Parameters
    ema_period = int(params.get("ema_period", METADATA["defaults"]["ema_period"]))
    ratio = float(params.get("imbalance_ratio", METADATA["defaults"]["imbalance_ratio"]))
    sl_pips = float(params.get("sl_pips", METADATA["defaults"]["sl_pips"]))
    tp_pips = float(params.get("tp_pips", METADATA["defaults"]["tp_pips"]))
    
    if data.empty:
        return pd.Series(dtype=bool), pd.Series(dtype=bool), None
    
    close = data['close']
    
    # 1. Macro Filter: Price > EMA(200)
    ema = vbt.MA.run(close, ema_period)
    trend_filter = close > ema.ma
    
    # 2. Imbalance Detection
    imbalance_signal = _calculate_imbalance_series(data, ratio)
        
    # 3. Entry Logic
    # Aggressive Buy on Imbalance Candle if Trend is Up
    entries = trend_filter & imbalance_signal
    exits = pd.Series(False, index=entries.index) # No fixed exit signal, use SL/TP
    
    # 4. Construct Signal Dict (for Live Execution)
    latest_msg = "NEUTRAL"
    latest_trigger = bool(entries.iloc[-1])
    
    if latest_trigger:
        latest_msg = "BULLISH"
        
    latest_signal = {
        "direction": latest_msg,
        "stop_loss": float(close.iloc[-1] - (sl_pips * 0.0001)), 
        "take_profit": float(close.iloc[-1] + (tp_pips * 0.0001)),
        "reason": f"Imbalance (Ratio {ratio}) + UpTrend (EMA {ema_period})",
        "metadata": {
            "strategy_name": METADATA["name"],
            "trend_ok": bool(trend_filter.iloc[-1]),
            "imbalance_detected": bool(imbalance_signal.iloc[-1]),
            "current_price": float(close.iloc[-1]),
            "ema_value": float(ema.ma.iloc[-1])
        }
    }
    
    return entries, exits, latest_signal
