
import pytest
import pandas as pd
import numpy as np
from app.indicators.market_profile import calculate_market_profile
from app.indicators.correlation import calculate_correlation
from app.indicators.positioning import detect_crowding, calculate_max_pain
from app.indicators.pivots import calculate_pivots, calculate_all_pivots
from app.indicators.price_action import detect_pin_bar, detect_inside_bar, detect_engulfing

def test_market_profile_coverage():
    df = pd.DataFrame({
        "open": [100.0]*24,
        "high": [105.0]*24,
        "low": [95.0]*24,
        "close": [100.0]*24,
        "volume": [1000.0]*24
    })
    df.index = pd.date_range("2024-01-01", periods=24, freq="H")
    
    res = calculate_market_profile(df)
    assert "poc" in res
    assert "vah" in res
    assert "val" in res

def test_correlation_coverage():
    series_a = pd.Series(np.random.normal(100, 1, 100))
    series_b = pd.Series(np.random.normal(100, 1, 100))
    
    res = calculate_correlation(series_a, series_b)
    assert "correlation" in res
    assert "regime" in res

def test_positioning_coverage():
    # Test detect_crowding
    res = detect_crowding(
        call_oi=[100, 200, 300],
        put_oi=[300, 200, 100],
        strikes=[1900, 2000, 2100],
        current_price=2000
    )
    assert "crowding_regime" in res
    
    assert "max_pain_strike" in res

def test_pivots_coverage():
    df = pd.DataFrame({
        "high": [110, 115, 120, 125, 130],
        "low": [90, 95, 100, 105, 110],
        "close": [100, 110, 120, 115, 125]
    })
    df.index = pd.date_range("2024-01-01", periods=5, freq="D")
    
    # Test different methods
    for method in ['traditional', 'camarilla', 'woodie']:
        res = calculate_pivots(df, method=method)
        assert not res.empty
        
    # Test all pivots
    res_all = calculate_all_pivots(df, timeframes=['Daily'])
    assert not res_all.empty

def test_price_action_coverage():
    df = pd.DataFrame({
        "open": [100, 100, 100],
        "high": [110, 105, 110],
        "low": [80, 95, 90],
        "close": [100, 101, 110]
    })
    df.index = pd.date_range("2024-01-01", periods=3, freq="H")
    
    res_pin = detect_pin_bar(df)
    assert len(res_pin) == 3
    
    res_inside = detect_inside_bar(df)
    assert len(res_inside) == 3
    
    res_engulf = detect_engulfing(df)
    assert len(res_engulf) == 3
