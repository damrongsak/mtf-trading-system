import pandas as pd
import numpy as np
import pytest
from app.indicators import calculate_ema, calculate_atr

def test_calculate_ema():
    close = pd.Series([10, 11, 12, 13, 14])
    ema = calculate_ema(close, span=2)
    
    assert len(ema) == 5
    assert ema.iloc[-1] > ema.iloc[0]
    # First value should be same as close
    assert ema.iloc[0] == 10

def test_calculate_atr():
    high = pd.Series([10, 11, 12, 13, 14])
    low = pd.Series([9, 10, 11, 12, 13])
    close = pd.Series([9.5, 10.5, 11.5, 12.5, 13.5])
    
    atr = calculate_atr(high, low, close, window=2)
    
    assert len(atr) == 5
    # ATR should be positive (or NaN at start)
    assert atr.iloc[-1] > 0
