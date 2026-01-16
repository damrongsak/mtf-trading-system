
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from app.strategies.hybrid_alpha_v1.strategy import strategy as hybrid_alpha_strategy

@pytest.mark.asyncio
async def test_hybrid_alpha_low_score():
    # Scenario: Price is rising but not enough for Alpha Threshold
    # Mock State
    state = MagicMock()
    state.symbol = "TEST"
    state.config_json = {"alpha_threshold": 0.95} # Very high threshold
    
    # Mock DataManager
    dates = pd.date_range("2023-01-01", periods=100, freq="15min")
    # Linear growth rank will be high, but let's control it.
    close = pd.Series(np.linspace(100, 110, 100), index=dates)
    df = pd.DataFrame({
        "open": close, "high": close+1, "low": close-1, "close": close, "volume": 1000
    })
    
    dm = MagicMock()
    dm.get_data.return_value = df
    
    # Execute
    result = await hybrid_alpha_strategy(state, dm)
    assert result is None # Should fail alpha check if threshold is very high or logic mismatch

@pytest.mark.asyncio
async def test_hybrid_success():
    # Scenario: High Alpha + Order Block Bounce
    state = MagicMock()
    state.symbol = "TEST"
    state.config_json = {"alpha_threshold": 0.1} # Low threshold to pass alpha
    
    # Create Data:
    # 1. Formation of Bullish OB at index 50
    # 2. Rally up
    # 3. Pullback to OB at index 99
    
    dates = pd.date_range("2023-01-01", periods=100, freq="15min")
    open_p = np.full(100, 100.0)
    close_p = np.full(100, 100.0)
    high_p = np.full(100, 101.0)
    low_p = np.full(100, 99.0)
    
    # Index 50: Down candle (Red)
    open_p[50] = 100.0
    close_p[50] = 98.0 # Down
    
    # Index 51: Big Up drive (Green - Engulfing) -> Creates Bullish OB at [98, 100] (Body of prev)
    open_p[51] = 98.0
    close_p[51] = 105.0 
    
    # Index 99: Price comes back to 99.0 (Inside OB 98-100)
    open_p[99] = 100.0
    close_p[99] = 100.1 # Bounce off Top (100.0) -> Valid Trigger
    
    volume_p = np.full(100, 1000)
    volume_p[51] = 2000 # Spike for OB confirmation
    
    df = pd.DataFrame({
        "open": open_p, "high": high_p, "low": low_p, "close": close_p, "volume": volume_p
    }, index=dates)
    
    dm = MagicMock()
    dm.get_data.return_value = df
    
    # Execute
    result = await hybrid_alpha_strategy(state, dm)
    
    assert result is not None
    assert result['direction'] == "BULLISH"
    assert "Hybrid" in result['reason']
    assert result['metadata']['ob_index'] == 50
