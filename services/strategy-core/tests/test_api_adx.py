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
        
        from unittest.mock import AsyncMock
        
        mock_worker_instance = MockIndicatorWorker.return_value
        mock_worker_instance.start = AsyncMock()
        mock_worker_instance.stop = AsyncMock()
        
        mock_se_start.side_effect = AsyncMock()
        mock_lr_start.side_effect = AsyncMock()
        mock_fleet.side_effect = AsyncMock()

        with TestClient(app) as c:
            yield c

def test_get_adx_endpoint(client):
    # 1. Create synthetic OHLC data
    # ADX requires High, Low, Close. 
    # We'll create a small trend to ensure ADX isn't 0 everywhere, though random is fine for schema check.
    # Length of 50 to accommodate default lookback (14)
    
    n_candles = 50
    # Create a nice up trend
    close = [100 + i + (i%5) for i in range(n_candles)]
    high = [c + 2 for c in close]
    low = [c - 2 for c in close]
    
    payload = {
        "high": high,
        "low": low,
        "close": close,
        "length": 14
    }
    
    # 2. Call the endpoint
    response = client.post("/api/v1/calculate/adx", json=payload)
    
    # 3. Verify Response Code
    assert response.status_code == 200, f"Error: {response.text}"
    
    # 4. Verify Schema
    data = response.json()
    assert "adx" in data
    assert "dmp" in data
    assert "dmn" in data
    
    # 5. Verify Data Integrity
    # Length of output should match input length (padded with nulls/nans)
    assert len(data["adx"]) == n_candles
    assert len(data["dmp"]) == n_candles
    assert len(data["dmn"]) == n_candles
    
    # Check that we have valid floats at the end (after lookback period)
    # 14 (TR) + 14 (ADX smoothing) -> roughly 28-29 index start
    last_idx = -1
    assert isinstance(data["adx"][last_idx], float)
    assert isinstance(data["dmp"][last_idx], float)
    assert isinstance(data["dmn"][last_idx], float)
    
    # Basic logic check: ADX should be positive
    assert data["adx"][last_idx] >= 0

def test_get_adx_endpoint_insufficient_data(client):
    # Test with too few data points
    payload = {
        "high": [10, 11],
        "low": [9, 10],
        "close": [9.5, 10.5],
        "length": 14
    }
    
    response = client.post("/api/v1/calculate/adx", json=payload)
    
    # Expect 200 OK but empty or null filled arrays, OR 400 if validation strict.
    # Current implementation returns empty lists if adx_df is empty/None
    # OR it runs but produces all NaNs/Nones.
    # Let's check behavior. Trend.py: if adx_df is empty -> returns empty arrays.
    
    assert response.status_code == 200
    data = response.json()
    # Expect empty lists or lists of Nones depending on how pandas-ta handles 2 rows with length 14
    # Actually code says: if adx_df is None or empty: return [], [], []
    # pandas-ta usually returns DF with NaNs for short data, not empty.
    # So we expect lists of nulls potentially.
    
    # Let's assert we get a valid response structure at least
    assert "adx" in data
