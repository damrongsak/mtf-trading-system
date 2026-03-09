import pytest
from unittest.mock import AsyncMock, patch
from app.schemas.response import ResponseStatus

def test_get_volatility_proxy(client):
    mock_response = {
        "status": "success",
        "data": {
            "realized_vol": 0.15,
            "parkinson_vol": 0.12,
            "yang_zhang_vol": 0.0,
            "rolling_vol_series": [0.1, 0.12, 0.15]
        },
        "timestamp": "2023-10-27T10:00:00+00:00"
    }
    
    with patch("app.routers.analytics.strategy_client.get_volatility", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        response = client.get("/api/v1/analytics/volatility?symbol=XAUUSD")
        
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["realized_vol"] == 0.15

def test_get_var_proxy(client):
    mock_response = {
        "status": "success",
        "data": {
            "var_95": -0.02,
            "var_99": -0.03,
            "cvar_95": -0.025,
            "cvar_99": -0.035
        },
        "timestamp": "2023-10-27T10:00:00+00:00"
    }
    
    with patch("app.routers.analytics.strategy_client.get_var", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        response = client.get("/api/v1/analytics/var?symbol=XAUUSD")
        
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["var_95"] == -0.02

def test_get_factors_proxy(client):
    mock_response = {
        "status": "success",
        "data": {
            "beta": 1.1,
            "momentum": 0.05,
            "rsi": 55.0,
            "volatility_regime": "NORMAL"
        },
        "timestamp": "2023-10-27T10:00:00+00:00"
    }
    
    with patch("app.routers.analytics.strategy_client.get_factors", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        response = client.get("/api/v1/analytics/factors?symbol=XAUUSD")
        
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["volatility_regime"] == "NORMAL"

def test_get_drawdown_proxy(client):
    mock_response = {
        "status": "success",
        "data": {
            "max_drawdown": -0.1,
            "current_drawdown": -0.02,
            "dd_duration": 10,
            "recovery_factor": 1.5
        },
        "timestamp": "2023-10-27T10:00:00+00:00"
    }
    
    with patch("app.routers.analytics.strategy_client.get_drawdown", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        response = client.get("/api/v1/analytics/drawdown?symbol=XAUUSD")
        
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["max_drawdown"] == -0.1
