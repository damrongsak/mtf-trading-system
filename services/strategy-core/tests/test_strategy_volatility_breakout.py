
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, AsyncMock
from app.strategies.volatility_breakout.strategy import strategy as volatility_breakout_strategy

@pytest.mark.asyncio
async def test_volatility_breakout_long():
    """
    Test BULLISH breakout scenario.
    """
    # 1. Setup Data
    # Need > 40 data points.
    dates = pd.date_range(start="2023-01-01", periods=100, freq='D')
    
    # Base price 100
    close = pd.Series(100.0, index=dates)
    high = pd.Series(105.0, index=dates)
    low = pd.Series(95.0, index=dates)
    
    # Create Normal Volatility (Bars 0-70) - Range 2.0
    close.iloc[0:70] = 100.0
    high.iloc[0:70] = 101.0
    low.iloc[0:70] = 99.0
    
    # Create Compression (Bars 70-98) - Range 0.5 (Very tight)
    # ATR will drop quickly. SMA will drop slowly.
    # ATR < SMA should be true here.
    close.iloc[70:99] = 100.0
    high.iloc[70:99] = 100.25
    low.iloc[70:99] = 99.75
    
    # Breakout Bar (99)
    # Price explodes Up to 110.
    close.iloc[99] = 110.0
    high.iloc[99] = 110.0 
    low.iloc[99] = 99.75
    
    # Keltner will be around 100 +/- (2 * ATR).
    # ATR(14) of data 101-99=2 is 2.
    # Upper Keltner ~ 100 + 4 = 104.
    # Close 110 > 104 -> Breakout!
    
    df = pd.DataFrame({'open': close, 'high': high, 'low': low, 'close': close})
    
    # 2. Config
    params = {"keltner_mult": 2.0}
    
    # 3. Run (Sync)
    entries, exits, signal = volatility_breakout_strategy(df, params)
    
    # 4. Assert
    assert signal is not None
    assert signal['direction'] == "BULLISH"
    assert "Volatility Breakout Up" in signal['reason']
    assert signal['metadata']['volatility']['regime'] == "EXPANSION (Exiting Compression)"
    # At breakout, ATR spikes, so current ratio should be > 1.0 (Expansion)
    # The Strategy checked if PREVIOUS ratio was < 1.0 (Compression)
    assert signal['metadata']['volatility']['compression_ratio'] > 1.0 
    
    # Check AI metadata
    assert "atr_14" in signal['metadata']['volatility']
    assert "technical" in signal['metadata']
    
    # Check Series
    assert entries is not None
    assert isinstance(entries, pd.Series)
    assert entries.iloc[-1] == True

@pytest.mark.asyncio
async def test_volatility_no_breakout():
    """
    Test scenario with no breakout.
    """
    dates = pd.date_range(start="2023-01-01", periods=100, freq='D')
    close = pd.Series(100.0, index=dates)
    high = pd.Series(102.0, index=dates)
    low = pd.Series(98.0, index=dates)
    
    df = pd.DataFrame({'open': close, 'high': high, 'low': low, 'close': close})
    
    params = {}
    
    entries, exits, signal = volatility_breakout_strategy(df, params)
    
    assert signal is None
    # Entries should be all false (or None)
    if entries is not None:
        assert not entries.iloc[-1]
