
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch, AsyncMock
from app.indicators.piv import calculate_n_bands, calculate_piv_levels
from app.indicators.trend import calculate_adx, detect_trend_structure
from app.indicators.volume import calculate_volume_profile
from app.strategies.alpha_engine_v1.strategy import strategy as alpha_strategy
from app.strategies.oi_gamma_v1.strategy import strategy_vectorized

def test_piv_indicators_deep():
    df = pd.DataFrame({
        "close": [10.0, 11.0, 12.0, 11.0, 10.0] * 20,
        "high": [11.0, 12.0, 13.0, 12.0, 11.0] * 20,
        "low": [9.0, 10.0, 11.0, 10.0, 9.0] * 20,
        "volume": [100.0] * 100
    })
    bands = calculate_n_bands(df, gvz=20.0)
    # Correct assertion for keys returned by piv indicators
    assert "n_band_upper_1.0" in bands
    
    levels = calculate_piv_levels(df, gvz=20.0)
    assert len(levels) > 0

def test_trend_indicators_deep():
    data = pd.DataFrame({
        "high": [100.0] * 100,
        "low": [90.0] * 100,
        "close": [95.0] * 100
    })
    data["high"] = data["high"] + np.random.normal(0, 1, 100)
    data["low"] = data["low"] - np.random.normal(0, 1, 100)
    data["close"] = (data["high"] + data["low"]) / 2
    
    adx = calculate_adx(data["high"], data["low"], data["close"], length=5)
    assert adx is not None
    
    struct = detect_trend_structure(data["high"], data["low"], data["close"], length=5)
    assert struct is not None

def test_alpha_engine_logic():
    # alpha_strategy is synchronous
    df = pd.DataFrame({"close": [100, 101, 102], "high": [103, 104, 105], "low": [98, 99, 100], "volume": [1, 2, 3]})
    df.index = pd.date_range("2024-01-01", periods=3, freq="H")
    
    params = {"formula": "close * 1.5"}
    
    # Correct call (sync)
    entries, exits, signal = alpha_strategy(df, params=params)
    assert entries is not None

def test_oi_gamma_vectorized_logic():
    df = pd.DataFrame({
        "close": [2000.0]*10,
        "high": [2005.0]*10,
        "low": [1995.0]*10
    })
    df.index = pd.date_range("2024-01-01", periods=10, freq="H")
    
    oi_data = [
        {'strike': 2010.0, 'call_oi': 1000.0, 'put_oi': 500.0, 'underlying_price': 2000.0},
        {'strike': 1990.0, 'call_oi': 500.0, 'put_oi': 1000.0, 'underlying_price': 2000.0}
    ]
    
    with patch("app.strategies.oi_gamma_v1.strategy.fetch_latest_oi_snapshot", return_value={"records": oi_data}):
        res = strategy_vectorized(df)
        assert res is not None
