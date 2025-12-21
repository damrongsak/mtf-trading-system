from app.schemas.response import ResponseStatus
from app.models.backtest_profile import BacktestHistory
import uuid

from unittest.mock import AsyncMock, patch, MagicMock

def test_run_backtest(client):
    payload = {
        "strategy_id": str(uuid.uuid4()),
        "symbol": "XAUUSD",
        "timeframe": "15m",
        "start_date": "2023-01-01T00:00:00",
        "end_date": "2023-01-02T00:00:00",
        "initial_capital": 10000.0
    }
    
    mock_result = {
        "id": "123",
        "status": "COMPLETED",
        "metrics": {
            "total_return": 100.0,
            "total_return_percent": 1.0,
            "max_drawdown": 10.0,
            "max_drawdown_percent": 0.1,
            "win_rate": 0.5,
            "sharpe_ratio": 1.0,
            "total_trades": 10,
            "winning_trades": 5,
            "losing_trades": 5
        },
        "trades": [],
        "best_params": None,
        "all_results": None
    }
    
    with patch("app.routers.backtest.strategy_client.run_backtest", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = mock_result
        response = client.post("/api/v1/backtest/run", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    # Verify key metrics are present
    assert data["data"]["id"] == mock_result["id"]
    assert data["data"]["status"] == mock_result["status"]
    assert data["data"]["metrics"]["sharpe_ratio"] == mock_result["metrics"]["sharpe_ratio"]

def test_get_backtest_results(client, mock_db_session):
    backtest_id = uuid.uuid4()
    
    # Mock DB history entry
    mock_history = MagicMock(spec=BacktestHistory)
    mock_history.id = backtest_id
    mock_history.status = "COMPLETED"
    mock_history.metrics = {
        "total_return": 100.0,
        "total_return_percent": 1.0,
        "max_drawdown": 10.0,
        "max_drawdown_percent": 0.1,
        "win_rate": 0.5,
        "sharpe_ratio": 1.5,
        "total_trades": 10,
        "winning_trades": 5,
        "losing_trades": 5
    }
    mock_history.best_params = None
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_history
    
    response = client.get(f"/api/v1/backtest/results/{backtest_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ResponseStatus.SUCCESS
    assert data["data"]["id"] == str(backtest_id)
    assert data["data"]["metrics"]["sharpe_ratio"] == 1.5
