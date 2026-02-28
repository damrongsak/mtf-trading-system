import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def mock_startup():
    with patch("app.main.strategy_engine.start", new_callable=AsyncMock) as mock_engine_start, \
         patch("app.main.live_runner.start", new_callable=AsyncMock) as mock_runner_start, \
         patch("app.fleet.FleetManager.get_instance") as mock_fleet, \
         patch("app.main.live_runner.stop", new_callable=AsyncMock), \
         patch("app.main.reconciliation_worker.start", new_callable=AsyncMock):
            
        mock_fleet_instance = MagicMock()
        mock_fleet_instance.load_fleet = AsyncMock()
        mock_fleet.return_value = mock_fleet_instance
        yield

@pytest.fixture
def client(mock_startup):
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_db_session():
    with patch("app.engine.router.SessionLocal") as mock_db:
        yield mock_db

@pytest.fixture
def mock_fetch_data():
    with patch("app.engine.router.fetch_data_from_db") as mock_fetch:
        yield mock_fetch

@pytest.fixture
def mock_resolve_symbol():
    with patch("app.engine.router.resolve_market_symbol_id") as mock_resolve:
        mock_resolve.return_value = "00000000-0000-0000-0000-000000000000"
        yield mock_resolve

def create_mock_df(rows=200):
    dates = pd.date_range("2023-01-01", periods=rows, freq="H")
    return pd.DataFrame({
        "open": np.random.rand(rows),
        "high": np.random.rand(rows),
        "low": np.random.rand(rows),
        "close": np.random.rand(rows),
        "volume": np.random.randint(100, 1000, rows)
    }, index=dates)

def test_alpha_preview_success(client, mock_db_session, mock_fetch_data, mock_resolve_symbol):
    # Mock Data
    mock_fetch_data.return_value = create_mock_df(150)
    
    payload = {
        "formula": "(close > open) * 1.0", # Force float to avoid numpy bool serialization issues
        "symbol": "EUR_USD",
        "timeframe": "H1"
    }
    
    response = client.post("/api/v1/alpha/preview", json=payload)
    
    if response.status_code != 200:
        print(f"DEBUG FAILURE: {response.text}")
        
    assert response.status_code == 200
    expected_limit = 100
    data = response.json()
    assert len(data["signal"]) == expected_limit # Should slice to limit
    assert len(data["timestamps"]) == expected_limit
    assert "sharpe" in data["metrics"]

def test_alpha_test_full_run_success(client, mock_db_session, mock_fetch_data, mock_resolve_symbol):
    # Mock Data
    mock_fetch_data.return_value = create_mock_df(500)
    
    payload = {
        "formula": "ts_rank(close, 10)",
        "symbol": "EUR_USD",
        "timeframe": "H1"
    }
    
    response = client.post("/api/v1/alpha/test", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["signal"]) == 500 # Full length
    assert "sharpe" in data["metrics"]

def test_alpha_symbol_not_found(client, mock_db_session, mock_fetch_data):
    # Mock resolve failing even for default
    with patch("app.engine.router.resolve_market_symbol_id", return_value=None):
        payload = {
            "formula": "close",
            "symbol": "INVALID",
            "timeframe": "H1"
        }
        response = client.post("/api/v1/alpha/preview", json=payload)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

def test_alpha_formula_error(client, mock_db_session, mock_fetch_data, mock_resolve_symbol):
    mock_fetch_data.return_value = create_mock_df(50)
    
    payload = {
        "formula": "invalid_func(close)", # Should trigger eval error
        "symbol": "EUR_USD",
        "timeframe": "H1"
    }
    
    response = client.post("/api/v1/alpha/preview", json=payload)
    # The router catches invalid formulas as 400
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert any(x in detail for x in ["Evaluation Error", "Security", "not supported"])

def test_alpha_empty_data(client, mock_db_session, mock_fetch_data, mock_resolve_symbol):
    mock_fetch_data.return_value = pd.DataFrame() # Empty
    
    payload = {
        "formula": "close",
        "symbol": "EUR_USD",
        "timeframe": "H1"
    }
    
    response = client.post("/api/v1/alpha/preview", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["signal"] == []
    assert data["timestamps"] == []
