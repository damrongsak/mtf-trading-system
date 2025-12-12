from datetime import datetime
from unittest.mock import MagicMock
from app.models.candle import Candle

def test_get_candles(client, mock_db_session):
    # Setup mock query chain
    mock_query = MagicMock()
    mock_db_session.query.return_value = mock_query
    
    # Allow chaining
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    # Setup return data
    mock_candles = [
        MagicMock(
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            open=1.1, high=1.2, low=1.0, close=1.15, volume=1000,
            symbol="EUR_USD", timeframe="H1"
        ),
        MagicMock(
            timestamp=datetime(2023, 1, 1, 11, 0, 0),
            open=1.05, high=1.1, low=1.0, close=1.08, volume=900,
            symbol="EUR_USD", timeframe="H1"
        )
    ]
    # The router reverses the list, so we mock it returning them in desc order (latest first)
    mock_query.limit.return_value.all.return_value = mock_candles

    response = client.get("/api/v1/market/candles?symbol=EUR_USD&timeframe=H1&count=2")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]) == 2
    # Verify order was reversed (to ascending)
    # Original list: [12:00, 11:00] (desc)
    # Expected result: [11:00, 12:00] (asc)
    # Wait, simple list reverse of mock objects.
    # The first item in response should be the last item in mock_candles
    
    assert data["data"][0]["close"] == 1.08
    assert data["data"][1]["close"] == 1.15
