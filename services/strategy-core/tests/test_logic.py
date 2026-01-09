import pandas as pd
import pytest
from app.logic import check_macro_bias, check_trigger, SignalDirection

def test_macro_bias_bullish():
    # Close > EMA200
    # Use enough data points
    df = pd.DataFrame({
        'close': [100.0] * 300
    })
    # Make last completed candle higher than EMA
    df.iloc[-2, df.columns.get_loc('close')] = 110.0
    
    # EMA(200) of 100 is 100. Last completed close 110 > 100 -> Bullish
    bias = check_macro_bias(df)
    assert bias == SignalDirection.BULLISH

def test_macro_bias_bearish():
    # Close < EMA200
    df = pd.DataFrame({
        'close': [100.0] * 300
    })
    # Make last completed candle lower
    df.iloc[-2, df.columns.get_loc('close')] = 90.0
    
    bias = check_macro_bias(df)
    assert bias == SignalDirection.BEARISH

def test_check_trigger_bullish():
    # Needs at least 32 rows
    data = {
        'open': [100.0] * 35,
        'high': [105.0] * 35,
        'low': [95.0] * 35,
        'close': [100.0] * 35
    }
    df = pd.DataFrame(data)
    
    # Index -2 is the one checked for trigger
    # Open 100, Close 110, High 110, Low 100 -> Body 10, Range 10, Rv 1.0
    df.iloc[-2, df.columns.get_loc('open')] = 100.0
    df.iloc[-2, df.columns.get_loc('close')] = 110.0
    df.iloc[-2, df.columns.get_loc('high')] = 110.0
    df.iloc[-2, df.columns.get_loc('low')] = 100.0
    
    # Add some volatility in previous candles so Parkinson Vol > 0.0005
    # Parkinson uses High/Low
    df.iloc[-5, df.columns.get_loc('high')] = 120.0
    df.iloc[-5, df.columns.get_loc('low')] = 80.0
    
    triggered = check_trigger(df, SignalDirection.BULLISH)
    assert triggered == True

def test_check_trigger_fail_rv():
    data = {
        'open': [100.0] * 35,
        'high': [105.0] * 35,
        'low': [95.0] * 35,
        'close': [100.0] * 35
    }
    df = pd.DataFrame(data)
    
    # Index -2: Weak candle (lots of wick)
    # Open 100, Close 101, High 110, Low 90.
    # Body 1, Range 20. Rv = 0.05
    df.iloc[-2, df.columns.get_loc('open')] = 100.0
    df.iloc[-2, df.columns.get_loc('close')] = 101.0
    df.iloc[-2, df.columns.get_loc('high')] = 110.0
    df.iloc[-2, df.columns.get_loc('low')] = 90.0
    
    # Add volatility
    df.iloc[-5, df.columns.get_loc('high')] = 120.0
    df.iloc[-5, df.columns.get_loc('low')] = 80.0
    
    triggered = check_trigger(df, SignalDirection.BULLISH)
    assert triggered == False