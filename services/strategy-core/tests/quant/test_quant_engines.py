import pytest
import pandas as pd
import numpy as np
from app.quant.risk_map import risk_map_engine
from app.quant.positioning import positioning_engine

def test_risk_map_calculation():
    # Mock DataFrame
    dates = pd.date_range(start="2024-01-01", periods=100, freq="H")
    df = pd.DataFrame({
        "open": np.linspace(100, 110, 100),
        "high": np.linspace(101, 111, 100),
        "low": np.linspace(99, 109, 100),
        "close": np.linspace(100.5, 110.5, 100),
        "volume": [1000] * 100
    }, index=dates)
    
    result = risk_map_engine.compute_risk_score("XAUUSD", df)
    
    assert "composite_risk_score" in result
    assert "edge_score" in result
    assert 0 <= result["composite_risk_score"] <= 1.0
    assert result["symbol"] == "XAUUSD"

def test_positioning_sizing():
    # Mock Risk Map
    risk_map = {
        "edge_score": 0.8,
        "context": {"regime": "TRENDING_UP"},
        "layers": {"gamma_bias": "NEGATIVE"}
    }
    
    # 1% Risk on 10000 Equity is $100
    # Entry 100, SL 95 -> Distance 5
    # Since default max_risk_usd is 10.0, we will override it or use it. We'll instantiate a specific PositioningEngine for the test to avoid the $10 cap.
    from app.quant.positioning import PositioningEngine
    test_positioning_engine = PositioningEngine(default_max_risk_usd=1000.0)
    
    # Base Size = (10000 * 0.01) / 5 = 20
    # Multipliers: Regime (1.2), Edge (0.8), Gamma (1.1)
    # Expected Size = 20 * 1.2 * 0.8 * 1.1 = 21.12
    
    result = test_positioning_engine.calculate_lot_size(
        symbol="XAUUSD",
        entry_price=100.0,
        stop_loss=95.0,
        equity=10000.0,
        risk_map=risk_map
    )
    
    assert result["lot_size_units"] > 0
    assert result["risk_profile_source"] == "system_default"
    assert result["multipliers"]["regime"] == 1.2
    assert result["multipliers"]["edge"] == 0.8
    assert result["multipliers"]["gamma"] == 1.1
    assert pytest.approx(result["lot_size_units"], 0.001) == 21.12
