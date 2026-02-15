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


def test_get_batch_signals_with_objects(client):
    broker = "CTRADER"
    
    # Mock Symbols (returning objects like data-pipeline does)
    mock_symbols = [
        {"symbol": "XAUUSD", "id": "uuid-1"},
        {"symbol": "EURUSD", "id": "uuid-2"}
    ]
    
    # Mock Candles Response (Needs at least 10 candles)
    mock_candles = {
        "status": "success",
        "data": [
            {"timestamp": f"2023-01-01T00:0{i}:00", "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05, "volume": 100}
            for i in range(10)
        ]
    }
    
    # Mock Strategy Core Response
    mock_smc_batch = {
        "results": {
            "XAUUSD": {"institutional_bias": "BULLISH", "strategic_reasoning": "Test"},
            "EURUSD": {"institutional_bias": "BEARISH", "strategic_reasoning": "Test"}
        }
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        
        # mock_get sequence: 1. symbols, 2. XAUUSD candles, 3. EURUSD candles
        def side_effect(url, **kwargs):
            m = MagicMock(status_code=200)
            m.raise_for_status = MagicMock()
            if "/symbols" in url:
                m.json = lambda: mock_symbols
            elif "/candles" in url:
                m.json = lambda: mock_candles
            return m
            
        mock_get.side_effect = side_effect
        
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.json = lambda: mock_smc_batch
        mock_post.return_value.raise_for_status = MagicMock()
        
        response = client.post(
            "/api/v1/signal/batch",
            json={"broker": broker}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert len(data["data"]) == 2
    # Verify symbols were matched correctly
    symbols = [s["symbol"] for s in data["data"]]
    assert "XAUUSD" in symbols
    assert "EURUSD" in symbols
