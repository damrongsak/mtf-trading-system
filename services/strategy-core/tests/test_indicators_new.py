
import pytest
import pandas as pd
import numpy as np
from app.indicators.volatility import calculate_adr

def test_calculate_adr():
    """
    Test ADR logic with simulated Daily data.
    """
    # Create 30 days of data
    dates = pd.date_range(start="2023-01-01", periods=30, freq='D')
    # Highs are 10 + i, Lows are 5 + i. Daily Range = 5.
    high = pd.Series(data=[10 + i for i in range(30)], index=dates)
    low = pd.Series(data=[5 + i for i in range(30)], index=dates)
    
    # Expected ADR(20) at day 29:
    # SMA of last 20 ranges. All ranges are 5.0. So SMA is 5.0.
    # The function returns a Series aligned with input.
    # Logic: shift(1). So today (day 29) gets SMA from day 8..28?
    
    adr = calculate_adr(high, low, window=20)
    
    # Check shape
    assert len(adr) == 30
    
    # Check value at end (should be 5.0)
    # The first 20 days might be NaN due to rolling window.
    # Window=20 requires 20 obs.
    # Rolling min_periods defaults to window size.
    
    # Day 0 to 19 (20 days) -> Day 19 has full window.
    # Shift(1) -> Day 20 has the value from Day 19.
    
    val = adr.iloc[-1] 
    assert abs(val - 5.0) < 0.001
    
def test_calculate_adr_intraday():
    """
    Test ADR logic with Intraday data (resampling).
    """
    # Create intraday data: 48 hours, hourly freq
    dates = pd.date_range(start="2023-01-01", periods=48, freq='H')
    
    # Day 1 (0-23h): Range 10. High 20, Low 10.
    # Day 2 (24-47h): Range 20. High 40, Low 20.
    
    vals = []
    for i in range(48):
        if i < 24: # Day 1
            vals.append(15) # avg
        else: # Day 2
            vals.append(30)
            
    high = pd.Series(data=vals, index=dates)
    low = pd.Series(data=vals, index=dates)
    
    # Override High/Low to create ranges
    # Day 1
    high.iloc[0:24] = 20
    low.iloc[0:24] = 10
    
    # Day 2
    high.iloc[24:48] = 40
    low.iloc[24:48] = 20
    
    # ADR(window=1)
    # Day 1 Range = 10.
    # Day 2 Range = 20.
    
    # ADR Series should have Day 1's ADR project onto Day 2?
    # Logic: daily_range -> rolling(1).mean() -> shift(1)
    
    # Daily Means:
    # 2023-01-01: 10.0
    # 2023-01-02: 20.0
    
    # Shifted:
    # 2023-01-01: NaN
    # 2023-01-02: 10.0
    
    # Realign to Hourly:
    # 2023-01-01 00:00 -> NaN
    # ...
    # 2023-01-02 00:00 -> 10.0 (The ADR from prev day)
    
    adr = calculate_adr(high, low, window=1)
    
    # Check random hour in Day 2
    idx_day2 = 30 # 30th hour
    assert abs(adr.iloc[idx_day2] - 10.0) < 0.001
