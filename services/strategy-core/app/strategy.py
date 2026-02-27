import pandas as pd
import numpy as np

# Registry to hold available strategies
STRATEGIES = {}

def register_strategy(name):
    def decorator(func):
        STRATEGIES[name] = func
        return func
    return decorator

@register_strategy("ma_crossover")
def ma_crossover(close_price: pd.Series, params: dict):
    fast_period = int(params.get("ema_fast", 10))
    slow_period = int(params.get("ema_slow", 20))
    
    print(f"INFO: Running MA Crossover Strategy: Fast={fast_period}, Slow={slow_period}")
    
    fast_ma = vbt.MA.run(close_price, fast_period)
    slow_ma = vbt.MA.run(close_price, slow_period)
    
    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)
    
    return entries, exits

@register_strategy("rsi_strategy")
def rsi_strategy(close_price: pd.Series, params: dict):
    period = int(params.get("rsi_period", 14))
    lower_threshold = int(params.get("rsi_lower", 30))
    upper_threshold = int(params.get("rsi_upper", 70))
    
    print(f"INFO: Running RSI Strategy: Period={period}, L={lower_threshold}, U={upper_threshold}")
    
    rsi = vbt.RSI.run(close_price, window=period)
    
    entries = rsi.rsi_crossed_below(lower_threshold)
    exits = rsi.rsi_crossed_above(upper_threshold)
    
    return entries, exits

def get_strategy(name):
    return STRATEGIES.get(name)
