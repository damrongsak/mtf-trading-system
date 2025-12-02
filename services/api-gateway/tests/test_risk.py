from unittest.mock import patch, MagicMock, AsyncMock
from app.schemas.response import ResponseStatus
import httpx

def test_check_risk_success(client):
    payload = {
        "risk_usd": 10.0,
        "sl_distance_usd": 5.0,
        "min_lot": 0.01
    }
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "can_execute": True,
        "reason": "Risk within limits",
        "lot": 0.1
    }
    
    # Mock httpx.AsyncClient
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        response = client.post("/api/v1/risk/check", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS
        assert data["data"]["can_execute"] is True

def test_check_risk_service_unavailable(client):
    payload = {
        "risk_usd": 10.0,
        "sl_distance_usd": 5.0,
        "min_lot": 0.01
    }
    
    with patch("httpx.AsyncClient.post", side_effect=httpx.RequestError("Connection failed")):
        response = client.post("/api/v1/risk/check", json=payload)
        
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == ResponseStatus.ERROR

def test_check_risk_service_error(client):
    payload = {
        "risk_usd": 10.0,
        "sl_distance_usd": 5.0,
        "min_lot": 0.01
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