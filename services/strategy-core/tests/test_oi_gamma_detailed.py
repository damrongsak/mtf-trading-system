
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import MagicMock, patch
from app.analysis.liquidity_profile import LiquidityProfileAnalyzer
from app.strategies.oi_gamma_v1.strategy import strategy_vectorized

def test_oi_gamma_vectorized_detailed():
    df = pd.DataFrame({
        "close": [2000]*200,
        "high": [2001]*200,
        "low": [1999]*200,
        "volume": [1000]*200
    })
    df.index = pd.date_range("2024-01-01", periods=200, freq="min")
    
    oi_history = {
        datetime.utcnow(): {
            "underlying_price": 2000.0,
            "records": [
                {"strike": 1900, "call_oi": 100, "put_oi": 1000, "dte": 10},
                {"strike": 2000, "call_oi": 1000, "put_oi": 1000, "dte": 10},
                {"strike": 2100, "call_oi": 5000, "put_oi": 100, "dte": 10},
            ]
        }
    }
    
    # Test vectorized
    res = strategy_vectorized(df, oi_history=oi_history)
    assert res is not None

def test_analyze_snapshot_deep():
    data = [
        {"strike": 1900, "call_oi": 100, "put_oi": 1000, "dte": 10},
        {"strike": 2000, "call_oi": 1000, "put_oi": 1000, "dte": 10},
        {"strike": 2100, "call_oi": 5000, "put_oi": 100, "dte": 10},
    ]
    from app.analysis.liquidity_profile import LiquidityProfileAnalyzer
    analyzer = LiquidityProfileAnalyzer()
    
    # Trigger all branches in analyze_snapshot
    res = analyzer.analyze_snapshot(data, current_spot_price=2000.0)
    assert "levels" in res
    assert "regime" in res
