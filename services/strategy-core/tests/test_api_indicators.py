
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from app.main import app

@pytest.fixture
def client():
    # Mock startup components to prevent background workers from starting
    # Patch the CLASS "IndicatorWorker" so that when instantiated it yields a mock
    with patch("app.workers.indicator_worker.IndicatorWorker") as MockIndicatorWorker, \
         patch("app.main.strategy_engine.start", new_callable=MagicMock) as mock_se_start, \
         patch("app.main.live_runner.start", new_callable=MagicMock) as mock_lr_start, \
         patch("app.fleet.FleetManager.load_fleet", new_callable=MagicMock) as mock_fleet:
        
        # Configure the mock instance to have an async start method
        mock_worker_instance = MockIndicatorWorker.return_value
        mock_worker_instance.start = MagicMock(return_value=None) # async mock handled by auto-magic? No.
        
        # For async methods, we usually need AsyncMock or return a specific Future?
        # Standard MagicMock can be awaited if __await__ is mocked, or just use AsyncMock (py3.8+)
        # unittest.mock.AsyncMock is available in 3.8+
        
        from unittest.mock import AsyncMock
        mock_se_start.side_effect = AsyncMock()
        mock_lr_start.side_effect = AsyncMock()
        mock_fleet.side_effect = AsyncMock()
        mock_worker_instance.start = AsyncMock()
        mock_worker_instance.stop = AsyncMock()
        
        with TestClient(app) as c:
            yield c

def test_get_macd_endpoint(client):
    # Create dummy data
    close_prices = [100.0 + i for i in range(50)]
    
    payload = {
        "close": close_prices,
        "fast": 12,
        "slow": 26,
        "signal": 9
    }
    
    response = client.post("/api/v1/calculate/macd", json=payload)
    
    assert response.status_code == 200, f"Error: {response.text}"
    
    data = response.json()
    assert "macd" in data
    assert "signal" in data
    assert "hist" in data
    
    # Ensure they are lists (iterables) and have correct length
    # Note: VectorBT MACD might result in NaNs at the beginning, so length matches input
    assert isinstance(data["hist"], list)
    assert len(data["hist"]) == len(close_prices)
    
    # Check that we actually got values (some nulls expected at start)
    # The last value should be a float (valid calculation for 50 points)
    assert isinstance(data["hist"][-1], float)

