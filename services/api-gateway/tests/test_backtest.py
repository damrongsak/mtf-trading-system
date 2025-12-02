from app.schemas.response import ResponseStatus
import uuid

def test_run_backtest(client):
    payload = {
        "strategy_id": str(uuid.uuid4()),
        "symbol": "XAUUSD",
        "timeframe": "15m",
        "start_date": "2023-01-01T00:00:00",
        "end_date": "2023-01-02T00:00:00",
        "initial_capital": 10000.0
    }
    
    response = client.post("/api/v1/backtest/run", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["status"] == "COMPLETED"
    assert "metrics" in data["data"]

def test_get_backtest_results(client):
    backtest_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/backtest/results/{backtest_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["id"] == backtest_id
