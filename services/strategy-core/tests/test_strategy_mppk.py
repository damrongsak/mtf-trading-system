import pytest
import pandas as pd
import numpy as np
from app.strategies.mppk_v1.strategy import strategy, METADATA

@pytest.fixture
def mock_data():
    # Create sample candles
    # 0-5: Random
    # 6: Pinbar candle at Support
    
    dates = pd.date_range(start="2024-01-01", periods=20, freq="1h")
    data = pd.DataFrame({
        "open": np.full(20, 100.0),
        "high": np.full(20, 105.0),
        "low": np.full(20, 95.0),
        "close": np.full(20, 100.0),
        "volume": np.full(20, 1000)
    }, index=dates)
    
    # CASE 1: Bullish Pinbar (PAT1) at Support
    # Body: 5 (100-105)
    # Wick: Needs to be >= 10
    # High = 105, Low = 85, Close = 104, Open = 100
    # Lower Wick = MIN(100, 104) - 85 = 15. Body = 4. 15 >= 8 (True)
    # Support: Low (85) should be lowest in window
    
    # We set previous low to be slightly higher so this is a new low/support
    data.loc[data.index[5], "open"] = 100.0
    data.loc[data.index[5], "close"] = 104.0
    data.loc[data.index[5], "high"] = 105.0
    data.loc[data.index[5], "low"] = 85.0 # Krob 85 ends with 5!
    
    # Ensure it's a local low
    data.loc[data.index[0:5], "low"] = 90.0
    
    # CASE 2: Bearish Engulfing (PAT2) at Resistance
    # i=10
    # prev (9): Green
    # curr (10): Red, Engulfs prev
    # Resistance: High should be local max
    
    # Set resistance context
    data.loc[data.index[0:10], "high"] = 110.0
    
    # Candle 9 (Prev)
    data.loc[data.index[9], "open"] = 112.0
    data.loc[data.index[9], "close"] = 114.0 # Green
    data.loc[data.index[9], "high"] = 115.0
    data.loc[data.index[9], "low"] = 111.0
    
    # Candle 10 (Curr) - Bearish Engulfing
    data.loc[data.index[10], "open"] = 115.0 # Higher open
    data.loc[data.index[10], "close"] = 110.0 # Lower close (engulfs 112)
    data.loc[data.index[10], "high"] = 120.0 # Pivot High (Krob 120!)
    data.loc[data.index[10], "low"] = 109.0
    
    return data

@pytest.mark.asyncio
async def test_mppk_pat1_buy(mock_data):
    """Test PAT1 (Pinbar) Buy Detection"""
    entries, exits, signal = strategy(mock_data)
    
    # Index 5 should be a Buy
    assert entries.iloc[5] == True
    
    # Check signal dict logic for the LAST candle?
    # Strategy returns stats for the *entire* series, but signal_dict is for the last one only.
    # To test signal_dict content for index 5, we would need to slice data ending at 5.
    
    slice_data = mock_data.iloc[:6] # 0 to 5
    _, _, sig = strategy(slice_data)
    
    assert sig["direction"] == "BULLISH"
    assert "PAT1" in sig["reason"]
    assert sig["metadata"]["krob_check"] == True # 85.0 % 5 == 0

@pytest.mark.asyncio
async def test_mppk_pat2_sell(mock_data):
    """Test PAT2 (Engulfing) Sell Detection"""
    entries, exits, signal = strategy(mock_data)
    
    # Index 10 should be a Sell
    assert exits.iloc[10] == True
    
    slice_data = mock_data.iloc[:11] # End at 10
    _, _, sig = strategy(slice_data)
    
    assert sig["direction"] == "BEARISH"
    assert "PAT2" in sig["reason"]
    assert sig["metadata"]["context"] == "Resistance"
    
@pytest.mark.asyncio
async def test_mppk_metadata():
    """Verify structure of Metadata"""
    assert METADATA["name"] == "Mae Pla Pakka Kiew (MPPK)"
    assert "tp_points" in METADATA["defaults"]
