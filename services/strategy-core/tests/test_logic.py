import pandas as pd
import pytest
from app.logic import check_macro_bias, check_trigger, SignalDirection

def test_macro_bias_bullish():
    # Close > EMA200
    df = pd.DataFrame({
        'close': [100.0] * 205
    })
    # Make last few candles higher than EMA
    df.iloc[-1, df.columns.get_loc('close')] = 110.0
    
    # EMA(200) of 100 is 100. Last close 110 > 100 -> Bullish
    bias = check_macro_bias(df)
    assert bias == SignalDirection.BULLISH

def test_macro_bias_bearish():
    # Close < EMA200
    df = pd.DataFrame({
        'close': [100.0] * 205
    })
    # Make last few candles lower
    df.iloc[-1, df.columns.get_loc('close')] = 90.0
    
    bias = check_macro_bias(df)
    assert bias == SignalDirection.BEARISH

def test_check_trigger_bullish():
    # M15 Vector Candle: Strong Green Body > Wick
    # Open=100, Close=110, High=110, Low=100 -> Body=10, Range=10, Rv=1.0
    df = pd.DataFrame({
        'open': [100.0, 100.0],
        'close': [100.0, 110.0],
        'high': [100.0, 110.0],
        'low': [100.0, 100.0]
    })
    
    # Needs 2 rows. Last completed is index 0? 
    # Logic: df.iloc[-2]. We need at least 2 rows.
    # Logic checks iloc[-2]. So we need to push a 'forming' candle at end?
    # Logic: if len < 2 return False.
    # Logic checks candle = df.iloc[-2].
    
    # Let's provide 3 rows. The Trigger candle is index 1. Index 2 is forming.
    df = pd.DataFrame({
        'open': [100.0, 100.0, 110.0],
        'close': [101.0, 110.0, 112.0],
        'high': [102.0, 110.0, 113.0],
        'low': [99.0, 100.0, 110.0]
    })
    # Index 1: Open 100, Close 110, High 110, Low 100.
    # Body 10, Range 10. Rv = 1.0 > 0.7. Green.
    
    triggered = check_trigger(df, SignalDirection.BULLISH)
    assert triggered == True

def test_check_trigger_fail_rv():
    # Weak candle (lots of wick)
    # Open 100, Close 101, High 110, Low 90.
    # Body 1, Range 20. Rv = 0.05
    df = pd.DataFrame({
        'open': [100.0, 100.0, 110.0],
        'close': [101.0, 101.0, 112.0],
        'high': [102.0, 110.0, 113.0],
        'low': [99.0, 90.0, 110.0]
    })
    
    triggered = check_trigger(df, SignalDirection.BULLISH)
    assert triggered == False
