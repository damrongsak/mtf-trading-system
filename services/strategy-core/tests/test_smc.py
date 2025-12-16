import pandas as pd
import pytest
from app.smc import detect_order_blocks, detect_fvg

def test_detect_bullish_ob():
    # Create a scenario for Bullish OB
    # Candle 1: Red (Down)
    # Candle 2: Green (Up) and Engulfing
    data = {
        'open': [10, 10, 10, 9],
        'high': [11, 11, 11, 12],
        'low': [9, 9, 9, 8],
        'close': [9, 9, 9, 11]
    }
    df = pd.DataFrame(data)
    
    # Logic:
    # i=3 (last candle)
    # prev (i=2): open=10, close=9 (Red)
    # curr (i=3): open=9, close=11 (Green)
    # curr_close (11) > prev_open (10) -> Engulfing
    
    obs = detect_order_blocks(df)
    assert len(obs) == 1
    assert obs[0]['type'] == 'bullish'
    assert obs[0]['index'] == 2
    assert obs[0]['top'] == 10
    assert obs[0]['bottom'] == 9

def test_detect_bearish_ob():
    # Create a scenario for Bearish OB
    # Candle 1: Green (Up)
    # Candle 2: Red (Down) and Engulfing
    data = {
        'open': [10, 10, 9.5, 12],
        'high': [11, 11, 11, 12],
        'low': [9, 9, 9, 8],
        'close': [11, 11, 10.5, 8]
    }
    # i=3
    # prev (i=2): O=9.5, C=10.5. Body=1. Up.
    # curr (i=3): O=12, C=8. Body=4. Down.
    # curr_close (8) < prev_open (9.5) -> Engulfs
    # curr_body (4) > prev_body (1) * 1.5 -> 4 > 1.5 -> True
    df = pd.DataFrame(data)
    
    # Logic:
    # i=3
    # prev (i=2): open=9, close=11 (Green)
    # curr (i=3): open=11, close=9 (Red)
    # curr_close (9) < prev_open (9) -> Engulfing
    
    obs = detect_order_blocks(df)
    assert len(obs) == 1
    assert obs[0]['type'] == 'bearish'
    assert obs[0]['index'] == 2
    assert obs[0]['top'] == 10.5
    assert obs[0]['bottom'] == 9.5

def test_detect_bullish_fvg():
    # Bullish FVG: Low[i] > High[i-2]
    # i=0: High=10
    # i=1: ...
    # i=2: Low=11
    data = {
        'open': [10, 11, 12],
        'high': [10, 12, 13],
        'low': [9, 10, 11],
        'close': [10, 12, 13]
    }
    df = pd.DataFrame(data)
    
    # i=2
    # high_1 (i-2=0) = 10
    # low_3 (i=2) = 11
    # 11 > 10 -> FVG
    
    fvgs = detect_fvg(df)
    assert len(fvgs) == 1
    assert fvgs[0]['type'] == 'bullish'
    assert fvgs[0]['top'] == 11
    assert fvgs[0]['bottom'] == 10

def test_detect_bearish_fvg():
    # Bearish FVG: High[i] < Low[i-2]
    # i=0: Low=10
    # i=1: ...
    # i=2: High=9
    data = {
        'open': [11, 10, 9],
        'high': [12, 11, 9],
        'low': [10, 9, 8],
        'close': [11, 10, 8]
    }
    df = pd.DataFrame(data)
    
    # i=2
    # low_1 (i-2=0) = 10
    # high_3 (i=2) = 9
    # 9 < 10 -> FVG
    
    fvgs = detect_fvg(df)
    assert len(fvgs) == 1
    assert fvgs[0]['type'] == 'bearish'
    assert fvgs[0]['top'] == 10
    assert fvgs[0]['bottom'] == 9
