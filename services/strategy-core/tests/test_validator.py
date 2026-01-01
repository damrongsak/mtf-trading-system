import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.proving_ground.validator import WalkForwardValidator
from app.foundry.base import SignalState

# Mock Data
@pytest.fixture
def mock_wfa_data():
    # Generate 365 days of data
    # Create a sinusoidal trend + noise
    N = 365 * 24 # Hourly data for a year
    dates = pd.date_range(start="2024-01-01", periods=N, freq="1h")
    
    t = np.linspace(0, 4*np.pi, N)
    price = 100 + 10 * np.sin(t) + np.random.normal(0, 0.5, N)
    
    df = pd.DataFrame({
        'open': price - 0.1,
        'high': price + 0.5,
        'low': price - 0.5,
        'close': price,
        'volume': 1000
    }, index=dates)
    
    return df

def test_wfa_execution(mock_wfa_data):
    # Config: Trend Following EMA Cross
    # Optimization: Period [10, 50, 10]
    
    config = {
        "logic_blocks": [
            {
                "id": "TREND_EMA_CROSS",
                "name": "Trend",
                "parameters": {
                    "period": 20, # Default
                    "timeframe": "1h"
                }
            }
        ],
        "optimization": {
            "param_grid": {
                "Trend_period": [10, 20, 50, 100]
            }
        },
        "train_window_days": 60,
        "test_window_days": 30,
        "step_days": 30
    }
    
    validator = WalkForwardValidator(config, mock_wfa_data)
    result = validator.run()
    
    assert 'robustness_score' in result
    assert result['period_count'] > 0
    assert 'details' in result
    assert len(result['details']) > 0
    
    # Check if params were actually optimized
    first_chunk = result['details'][0]
    best_params = first_chunk['best_params']
    
    # Since simulated data is perfect sine wave, some period should be best.
    # We just ensure it ran and produced metrics.
    assert first_chunk['oos_metrics']['total_return'] != 0 # Might be negative but not zero
    
def test_wfa_no_optimization(mock_wfa_data):
    # Config with NO optimization grid
    config = {
        "logic_blocks": [
            {
                "id": "TREND_EMA_CROSS",
                "parameters": {"period": 20, "timeframe": "1h"}
            }
        ],
        "train_window_days": 60,
        "test_window_days": 30
    }
    
    validator = WalkForwardValidator(config, mock_wfa_data)
    result = validator.run()
    
    assert result['period_count'] > 0
    # Should just use default params
