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
    assert fvgs[0]['bottom'] == 9

def test_detect_structure():
    from app.smc import detect_structure
    
    # Create a simple swing high pattern
    # 0: 10
    # 1: 12
    # 2: 15 (High)
    # 3: 12
    # 4: 10
    
    data = {
        'high': [10, 12, 15, 12, 10, 10, 10],
        'low':  [8,  10, 12, 10, 8, 8, 8],
        'close': [9, 11, 13, 11, 9, 9, 9],
        'open': [9, 9, 9, 9, 9, 9, 9]
    }
    df = pd.DataFrame(data)
    
    # Window=2 (default is 5 in code, let's override or use default data)
    # smc.py default window is 5.
    # To detect a high at 2 (15) with window 5, we need 5 bars before and 5 bars after? 
    # Or implies 5-bar lookback?
    # Mxwll logic uses `ta.pivothigh(high, length, length)` usually.
    # Our implementation uses rolling max. 
    # Let's test with enough data.
    
    # Using window=2 for the test if possible, or just generate more data.
    # Our detect_structure implementation allows window param.
    
    structure = detect_structure(df, window=2)
    
    # Should find a High at index 2
    # Left: 10, 12. Right: 12, 10. Max is 15 at index 2.
    
    assert structure is not None
    assert 'labels' in structure
    
    # Check for labels
    labels = structure['labels']
    # Example label: {'index': 2, 'text': 'HH', 'price': 15}
    # Note: Logic determines HH/LH based on previous high.
    # First high is usually just H or unmarked until confirmed? 
    # Let's check if it returns *something* for now to verify integration.
    
    # With a single high, it might be labeled based on initialization.
    # But it should detect the pivot.
    
    assert len(labels) > 0
    assert labels[0]['index'] == 2
    assert labels[0]['price'] == 15

def test_auto_fibs():
    from app.smc import calculate_auto_fibs
    
    # Create a massive Move Up
    # 0: 100
    # ...
    # 10: 200
    
    data = {
        'high': [100 + i*10 for i in range(11)],
        'low': [90 + i*10 for i in range(11)],
        'close': [95 + i*10 for i in range(11)],
        'open': [95 + i*10 for i in range(11)]
    }
    df = pd.DataFrame(data)
    
    fibs = calculate_auto_fibs(df, window=10)
    
    # High = 200, Low = 90 (at start)
    # Range = 110
    # Fib 0.5 = 90 + 55 = 145
    
    assert fibs is not None
    assert '0.5' in fibs
    assert fibs['0.5'] > 100

def test_detect_liquidity_sweeps():
    from app.smc import detect_liquidity_sweeps
    
    # Create sweep scenario
    # Window=5
    # 0-4: High=10
    # 5: High=11, Close=9 (Sweeps 10, Closes below) -> Bearish Sweep
    
    data = {
        'high': [10, 10, 10, 10, 10, 11],
        'low':  [8,  8,  8,  8,  8,  7],
        'close': [9, 9, 9, 9, 9, 9],
        'open': [9, 9, 9, 9, 9, 9]
    }
    df = pd.DataFrame(data)
    
    sweeps = detect_liquidity_sweeps(df)
    
    # In this case, High(11)>10 and Low(7)<8. Close(9) is between 8 and 10.
    # So it sweeps BOTH sides (Outside Bar).
    assert len(sweeps) == 2
    types = [s['type'] for s in sweeps]
    assert 'bearish_sweep' in types
    assert 'bullish_sweep' in types

def test_detect_ob_with_volume():
    from app.smc import detect_order_blocks
    
    # Bullish OB with Volume
    # i=20 (needs > 20 for volume check)
    # create 25 candles
    
    opens = [10] * 25
    closes = [10] * 25
    volumes = [100] * 25
    
    # i=23: Red Candle
    opens[23] = 10
    closes[23] = 9
    
    # i=24: Green Engulfing Candle with High Volume
    opens[24] = 9
    closes[24] = 11
    volumes[24] = 200 # > avg(100)
    
    data = {
        'open': opens,
        'high': [12]*25,
        'low': [8]*25,
        'close': closes,
        'volume': volumes
    }
    df = pd.DataFrame(data)
    
    obs = detect_order_blocks(df)
    
    # Should find one bullish OB at index 23
    assert len(obs) > 0
    # Find the one at 23
    ob = next((o for o in obs if o['index'] == 23), None)
    assert ob is not None
    assert ob['type'] == 'bullish'
    assert ob['strength'] == 'strong'
