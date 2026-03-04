import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.security import get_current_user
from app.models.strategy import Strategy
from app.models.user import User
from app.models.user_fund import Fund, UserFund, UserRole
from app.models.broker_account import BrokerAccount
import uuid
from datetime import datetime

@pytest.fixture
def local_mock_db():
    return MagicMock()

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    return user

from app.routers.auth import oauth2_scheme

@pytest.fixture(autouse=True)
def override_dependency(local_mock_db, mock_user):
    app.dependency_overrides[get_db] = lambda: local_mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[oauth2_scheme] = lambda: "dummy-token"
    yield
    app.dependency_overrides = {}

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_list_templates(client):
    response = client.get("/api/v1/strategies/templates", headers={"Authorization": "Bearer token"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 3
    assert data[0]["id"] == "SMC_V1"

def test_create_strategy_success(client, local_mock_db, mock_user):
    fund_id = uuid.uuid4()
    broker_id = uuid.uuid4()
    
    # Mock Fund existence
    mock_fund = MagicMock(spec=Fund)
    local_mock_db.query.return_value.filter.return_value.first.return_value = mock_fund
    
    # Refresh side effect to populate ID
    def refresh_effect(obj):
        obj.id = uuid.uuid4()
        obj.name = "My Strat"
        obj.fund_id = fund_id
        obj.broker_account_id = broker_id
        obj.template_id = "SMC"
        obj.config_json = {}
        obj.risk_settings = {}
        obj.is_active = False
        
    local_mock_db.refresh.side_effect = refresh_effect
    
    payload = {
        "name": "My Strat",
        "fund_id": str(fund_id),
        "template_id": "SMC",
        "broker_account_id": str(broker_id),
        "config_json": {},
        "risk_settings": {}
    }
    
    response = client.post("/api/v1/strategies/", json=payload, headers={"Authorization": "Bearer token"})
    if response.status_code != 200:
        print(f"DEBUG: {response.json()}")
        
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "My Strat"
    local_mock_db.add.assert_called_once()

def test_list_strategies(client, local_mock_db, mock_user):
    strat = MagicMock(spec=Strategy)
    strat.id = uuid.uuid4()
    strat.name = "Listed Strat"
    strat.template_id = "TPL"
    strat.broker_account_id = uuid.uuid4()
    strat.is_active = True
    strat.config_json = {}
    strat.risk_settings = {}
    
    # Mock chain: query(Strategy).join(Fund).join(UserFund).filter(...)
    q = local_mock_db.query.return_value.join.return_value.join.return_value.filter.return_value
    q.count.return_value = 1
    q.offset.return_value.limit.return_value.all.return_value = [strat]
    
    response = client.get("/api/v1/strategies/", headers={"Authorization": "Bearer token"})
    if response.status_code != 200:
        print(f"DEBUG: {response.json()}")
        
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["name"] == "Listed Strat"

@pytest.mark.asyncio
async def test_update_strategy_config_activate(client, local_mock_db):
    strat_id = uuid.uuid4()
    
    mock_strat = MagicMock(spec=Strategy)
    mock_strat.id = strat_id
    mock_strat.name = "Test Strategy" # Added name
    mock_strat.is_active = False # Initially Stopped
    mock_strat.config_json = {"param": 1}
    mock_strat.risk_settings = {}
    mock_strat.template_id = "TPL"
    mock_strat.broker_account_id = uuid.uuid4()
    
    local_mock_db.query.return_value.filter.return_value.first.return_value = mock_strat
    
    with patch("app.routers.strategy.strategy_client.start_strategy", new_callable=AsyncMock) as mock_start:
        payload = {"is_active": True, "config_json": {"param": 2}}
        response = client.post(f"/api/v1/strategies/{strat_id}/config", json=payload, headers={"Authorization": "Bearer token"})
        
        assert response.status_code == 200
        assert mock_strat.is_active is True
        assert mock_strat.config_json["param"] == 2
        
        # Verify side effect
        mock_start.assert_called_once()
        args, _ = mock_start.call_args
        assert args[0] == str(strat_id)
        assert args[1]["execution_mode"] == "AUTO"

@pytest.mark.asyncio
async def test_update_strategy_config_deactivate(client, local_mock_db):
    strat_id = uuid.uuid4()
    
    mock_strat = MagicMock(spec=Strategy)
    mock_strat.id = strat_id
    mock_strat.name = "Test Strategy" # Added name
    mock_strat.is_active = True # Initially Active
    mock_strat.template_id = "TPL"
    mock_strat.broker_account_id = uuid.uuid4()
    mock_strat.config_json = {}
    mock_strat.risk_settings = {}
    
    local_mock_db.query.return_value.filter.return_value.first.return_value = mock_strat
    
    with patch("app.routers.strategy.strategy_client.stop_strategy", new_callable=AsyncMock) as mock_stop:
        payload = {"is_active": False}
        response = client.post(f"/api/v1/strategies/{strat_id}/config", json=payload, headers={"Authorization": "Bearer token"})
        
        assert response.status_code == 200
        assert mock_strat.is_active is False
        
        mock_stop.assert_called_once_with(str(strat_id))

@pytest.mark.asyncio
async def test_start_strategy_endpoint(client, local_mock_db):
    strat_id = uuid.uuid4()
    mock_strat = MagicMock(spec=Strategy)
    mock_strat.id = strat_id
    mock_strat.is_active = False
    mock_strat.config_json = {}
    mock_strat.risk_settings = {}
    mock_strat.template_id = "TPL"
    mock_strat.broker_account_id = uuid.uuid4()
    
    local_mock_db.query.return_value.filter.return_value.first.return_value = mock_strat
    
    with patch("app.routers.strategy.strategy_client.start_strategy", new_callable=AsyncMock) as mock_start:
        response = client.post(f"/api/v1/strategies/{strat_id}/start", headers={"Authorization": "Bearer token"})
        assert response.status_code == 200
        assert mock_strat.is_active is True
        mock_start.assert_called_once()

@pytest.mark.asyncio
async def test_stop_strategy_endpoint(client, local_mock_db):
    strat_id = uuid.uuid4()
    mock_strat = MagicMock(spec=Strategy)
    mock_strat.id = strat_id
    mock_strat.is_active = True
    mock_strat.template_id = "TPL"
    mock_strat.broker_account_id = uuid.uuid4()
    mock_strat.config_json = {}
    mock_strat.risk_settings = {}
    
    local_mock_db.query.return_value.filter.return_value.first.return_value = mock_strat
    
    with patch("app.routers.strategy.strategy_client.stop_strategy", new_callable=AsyncMock) as mock_stop:
        response = client.post(f"/api/v1/strategies/{strat_id}/stop", headers={"Authorization": "Bearer token"})
        assert response.status_code == 200
        assert mock_strat.is_active is False
        mock_stop.assert_called_once()


@pytest.mark.asyncio
async def test_backtest_custom(client):
    payload = {
        "code": "print('hello')",
        "symbol": "XAU/USD",
        "timeframe": "1h",
        "start_date": "2024-01-01T00:00:00",
        "end_date": "2024-01-02T00:00:00",
        "initial_capital": 5000.0
    }
    
    with patch("app.routers.strategy.strategy_client.run_custom_backtest", new_callable=AsyncMock) as mock_bt:
        mock_bt.return_value = {"pnl": 100}
        
        response = client.post("/api/v1/strategies/backtest-custom", json=payload)
        assert response.status_code == 200
        assert response.json()["data"]["pnl"] == 100
        
        mock_bt.assert_called_once()
        args, _ = mock_bt.call_args
        assert args[0]["symbol"] == "XAU/USD"
