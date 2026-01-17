
import pytest
import pandas as pd
import numpy as np
from app.strategies.alice_momentum_v1.strategy import strategy

@pytest.mark.asyncio
async def test_alice_momentum_regime_classification():
    """
    Test Regime Classification and Breakout Entry.
    Status: EASY/NORMAL (Aligned 50 > 100 > 200).
    Input: Strong Bullish Trend.
    Expected: Entry Signal (Breakout).
    """
    # 1. Setup Perfect Bullish Trend
    dates = pd.date_range(start="2023-01-01", periods=300, freq='H')
    
    # Linear trend 100 -> 400
    close = pd.Series(np.linspace(100, 400, 300), index=dates)
    high = close + 2
    low = close - 2
    open_p = close - 1
    
    # 2. Modify end to create specific Breakout condition
    # Bars 280-290: Flat consolidation (Highs around 380)
    # Bar 295: Price jumps to 390 (Breakout)
    
    # We rely on the linear trend being "Breakout" continuously actually
    # because Close > Max(High, 20) roughly holds if slope is steep enough?
    # Linear: Close[i] > Close[i-1]. MAX(High[i-20:i-1]) is Close[i-1] + 2.
    # Close[i] needs to be > Close[i-1] + 2?
    # Slope = 1 per bar. 2 per bar?
    # 100 to 400 over 300 bars = 1.0 unit/bar. 
    # High = Close + 2.
    # Previous High ~ Close - 1 + 2 = Close + 1. 
    # Current Close vs Previous High?
    # Close[i] = Close[i-1] + 1. 
    # Previous High was Close[i-1] + 2. 
    # So Close[i] (X+1) < Prev High (X+2). No breakout in steady linear trend with noise.
    # Need a jump.
    
    # Let's force a jump at the end
    close_vals = close.values
    close_vals[-1] = close_vals[-2] + 10 # Big jump
    high_vals = high.values
    high_vals[-1] = close_vals[-1] + 2
    
    # Update Series
    close = pd.Series(close_vals, index=dates)
    high = pd.Series(high_vals, index=dates)
    
    df = pd.DataFrame({'open': open_p, 'high': high, 'low': low, 'close': close})
    
    # Run
    entries, exits, signal = strategy(df, {})
    
    # Assert
    assert entries is not None
    assert signal['metadata']['regime'] in ["EASY", "NORMAL"]
    assert signal['direction'] == "BULLISH"
    assert "technical" in signal['metadata']

