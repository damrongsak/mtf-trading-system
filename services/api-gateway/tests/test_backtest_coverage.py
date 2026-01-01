import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models.backtest_profile import BacktestConfig, BacktestHistory
from app.models.strategy import Strategy
from app.models.user_fund import Fund
import uuid
from datetime import datetime, timezone

@pytest.fixture
def local_mock_db():
    return MagicMock()

@pytest.fixture(autouse=True)
def override_dependency(local_mock_db):
    app.dependency_overrides[get_db] = lambda: local_mock_db
    yield
    app.dependency_overrides = {}

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_create_backtest_config(client, local_mock_db):
    payload = {
        "name": "My Config",
        "description": "Desc",
        "config": {
            "strategy_params": {"a": 1},
            "initial_capital": 1000,
            "broker_commission": 0.0,
            "slippage": 0.0,
             "start_date": datetime.now(timezone.utc).isoformat(),
             "end_date": datetime.now(timezone.utc).isoformat(),
             "symbol": "USD",
             "timeframe": "M1"
        }
    }
    
    def add_effect(obj):
        obj.id = uuid.uuid4()
        obj.created_at = datetime.now(timezone.utc)
        obj.name = "My Config"
        obj.description = "Desc"
        obj.config_json = payload["config"]
        
    local_mock_db.refresh.side_effect = add_effect
    
    response = client.post("/api/v1/backtest/configs", json=payload)
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "My Config"
    local_mock_db.add.assert_called_once()

def test_list_backtest_configs(client, local_mock_db):
    c = MagicMock(spec=BacktestConfig)
    c.id = uuid.uuid4()
    c.name = "C1"
    c.description = "desc" # Added description string
    c.config_json = {}
    c.created_at = datetime.now(timezone.utc)
    
    local_mock_db.query.return_value.order_by.return_value.all.return_value = [c]
    
    response = client.get("/api/v1/backtest/configs")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1

def test_list_history(client, local_mock_db):
    h = MagicMock(spec=BacktestHistory)
    h.id = uuid.uuid4()
    h.status = "COMPLETED"
    h.created_at = datetime.now(timezone.utc)
    h.metrics = {}
    h.best_params = {}
    h.execution_config = {}
    
    q = local_mock_db.query.return_value
    q.count.return_value = 1
    q.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [h]
    
    response = client.get("/api/v1/backtest/history")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1

@pytest.mark.asyncio
async def test_run_backtest(client, local_mock_db):
    # Strategy ID case
    strat_id = uuid.uuid4()
    payload = {
        "strategy_id": str(strat_id),
        "strategy_params": {"b": 2},
        "initial_capital": 5000,
        "broker_commission": 0,
        "slippage": 0,
        "symbol": "XAU/USD",
        "timeframe": "H1",
        "start_date": datetime.now(timezone.utc).isoformat(),
        "end_date": datetime.now(timezone.utc).isoformat()
    }
    
    # Mock Strategy
    strat = MagicMock(spec=Strategy)
    strat.config_json = {"a": 1}
    local_mock_db.query.return_value.filter.return_value.first.return_value = strat
    
    # Complete Metrics Mock
    mock_metrics = {
        "pnl": 100.0,
        "total_return": 100.0, # Added total_return
        "total_return_percent": 2.0,
        "max_drawdown": 50.0,
        "max_drawdown_percent": 1.0,
        "win_rate": 0.6,
        "total_trades": 10,
        "winning_trades": 6,
        "losing_trades": 4,
        "sharpe_ratio": 1.5,
        "sortino_ratio": 2.0
    }
    
    with patch("app.routers.backtest.strategy_client.run_backtest", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {
            "id": str(uuid.uuid4()), # Added ID
            "status": "COMPLETED", 
            "metrics": mock_metrics, 
            "best_params": {},
            "trades": [] 
        }
        
        response = client.post("/api/v1/backtest/run", json=payload)
        
        if response.status_code != 200:
             print(f"DEBUG: {response.json()}")
             
        assert response.status_code == 200
        # Check history update
        assert local_mock_db.add.called
        mock_run.assert_called_once()
        
@pytest.mark.asyncio
async def test_run_optimization(client):
    payload = {"k": "v"}
    with patch("app.routers.backtest.strategy_client.run_optimization", new_callable=AsyncMock) as mock_opt:
        mock_opt.return_value = {"status": "ok"}
        response = client.post("/api/v1/backtest/optimize", json=payload)
        assert response.status_code == 200
        mock_opt.assert_called_once()

@pytest.mark.asyncio
async def test_run_monte_carlo(client):
    payload = {"k": "v"}
    with patch("app.routers.backtest.strategy_client.run_monte_carlo", new_callable=AsyncMock) as mock_mc:
        mock_mc.return_value = {"sims": []}
        response = client.post("/api/v1/backtest/monte-carlo", json=payload)
        assert response.status_code == 200
        mock_mc.assert_called_once()
