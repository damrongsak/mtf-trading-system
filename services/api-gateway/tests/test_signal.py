from app.schemas.response import ResponseStatus

def test_get_latest_signal(client):
    symbol = "XAUUSD"
    response = client.get(f"/api/v1/signal/latest/{symbol}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["symbol"] == symbol.upper()
    assert "direction" in data["data"]

def test_check_signal(client):
    symbol = "EURUSD"
    response = client.post(
        "/api/v1/signal/check",
        params={"symbol": symbol}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["symbol"] == symbol.upper()
    assert data["data"]["reason"] == "Manual check triggered"
