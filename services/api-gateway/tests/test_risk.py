from unittest.mock import patch, MagicMock, AsyncMock
from app.schemas.response import ResponseStatus
import httpx

def test_check_risk_success(client):
    payload = {
        "symbol": "XAUUSD",
        "entry_price": 2000.0,
        "stop_loss": 1990.0,
        "risk_usd": 10.0
    }
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "symbol": "XAUUSD",
            "direction": "LONG",
            "risk_reward_ratio": 2.5,
            "position_size": {"units": 100, "lots": 1.0, "standard_lot_size": 100},
            "financials": {"risk_usd": 10.0, "profit_usd": 25.0, "account_balance": None},
            "is_safe": True,
            "warnings": []
        }
    }
    
    # Mock httpx.AsyncClient
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        response = client.post("/api/v1/risk/check", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS
        assert data["data"]["is_safe"] is True
        assert data["data"]["symbol"] == "XAUUSD"

def test_check_risk_service_unavailable(client):
    payload = {
        "symbol": "XAUUSD",
        "entry_price": 2000.0,
        "stop_loss": 1990.0,
        "risk_usd": 10.0
    }
    
    with patch("httpx.AsyncClient.post", side_effect=httpx.RequestError("Connection failed")):
        response = client.post("/api/v1/risk/check", json=payload)
        
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == ResponseStatus.ERROR

def test_check_risk_service_error(client):
    payload = {
        "symbol": "XAUUSD",
        "entry_price": 2000.0,
        "stop_loss": 1990.0,
        "risk_usd": 10.0
    }
    
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Bad Request", request=MagicMock(), response=mock_response)
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        response = client.post("/api/v1/risk/check", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == ResponseStatus.ERROR