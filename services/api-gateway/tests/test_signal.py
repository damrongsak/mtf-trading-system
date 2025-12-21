from app.schemas.response import ResponseStatus
from unittest.mock import patch, MagicMock, AsyncMock

def test_get_latest_signal(client):
    symbol = "XAUUSD"
    
    # Mock Data Pipeline and Strategy Core responses
    mock_candles = {
        "data": [
            {"timestamp": "2023-01-01T00:00:00", "open": 2000, "high": 2010, "low": 1990, "close": 2005, "volume": 100}
        ]
    }
    mock_smc = {
        "order_blocks": [{"type": "bullish", "top": 2010, "bottom": 1990, "mitigated": False}]
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json = lambda: mock_candles
        mock_get.return_value.raise_for_status = MagicMock()
        
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.json = lambda: mock_smc
        mock_post.return_value.raise_for_status = MagicMock()
        
        response = client.get(f"/api/v1/signal/latest/{symbol}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["symbol"] == symbol.upper()
    assert "direction" in data["data"]

def test_check_signal(client):
    symbol = "EURUSD"
    
    mock_candles = {
        "data": [
            {"timestamp": "2023-01-01T00:00:00", "open": 1.1000, "high": 1.1010, "low": 1.0990, "close": 1.1005, "volume": 100}
        ]
    }
    mock_smc = {"order_blocks": []}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json = lambda: mock_candles
        mock_get.return_value.raise_for_status = MagicMock()
        
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.json = lambda: mock_smc
        mock_post.return_value.raise_for_status = MagicMock()
        
        response = client.post(
            "/api/v1/signal/check",
            params={"symbol": symbol}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["symbol"] == symbol.upper()

