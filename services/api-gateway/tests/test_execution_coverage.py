import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.security import get_current_user
from app.models.trade import Trade, TradeStatus
from app.models.broker_account import BrokerAccount
from app.models.user_fund import Fund, UserFund, User, UserRole
import uuid

@pytest.fixture
def local_mock_db():
    return MagicMock()

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    return user

@pytest.fixture(autouse=True)
def override_dependency(local_mock_db, mock_user):
    app.dependency_overrides[get_db] = lambda: local_mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides = {}

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.mark.asyncio
async def test_get_account_summary(client, local_mock_db, mock_user):
    # Mock chain
    acc = MagicMock(spec=BrokerAccount)
    acc.id = uuid.uuid4()
    acc.broker_name = "OANDA"
    acc.credentials_encrypted = "enc"
    
    local_mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.first.return_value = acc
    
    with patch("app.routers.execution.execution_client.get_account_summary", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"balance": 1000}
        with patch("app.routers.execution.decrypt_data", return_value={"api_key": "k", "account_id": "a"}):
            response = client.get("/api/v1/execution/account/summary")
            assert response.status_code == 200
            assert response.json()["data"]["balance"] == 1000
            
            mock_get.assert_called_once()

@pytest.mark.asyncio
async def test_place_order_success(client, local_mock_db, mock_user):
    acc = MagicMock(spec=BrokerAccount)
    acc.id = uuid.uuid4()
    acc.broker_name = "OANDA"
    acc.credentials_encrypted = "enc"
    
    # Mock query for account
    local_mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.first.return_value = acc
    
    payload = {
        "symbol": "XAU/USD",
        "units": 1,
        "direction": "BUY"
    }

    with patch("app.routers.execution.execution_client.place_order", new_callable=AsyncMock) as mock_place:
        mock_place.return_value = {"id": "100", "price": 2000.0}
        
        with patch("app.routers.execution.decrypt_data", return_value={"api_key": "k", "account_id": "a"}):
            with patch("app.routers.execution.TradeService.create_trade_from_execution") as mock_create_trade:
                mock_trade = MagicMock(spec=Trade)
                mock_create_trade.return_value = mock_trade
                
                response = client.post("/api/v1/execution/orders", json=payload)
                
                assert response.status_code == 200
                assert response.json()["data"]["id"] == "100"
                mock_create_trade.assert_called_once()
                # Confirm trade.broker_account_id set
                assert mock_trade.broker_account_id == acc.id

@pytest.mark.asyncio
async def test_close_trade_success(client, local_mock_db, mock_user):
    # Mock Trade with broker link
    trade_id = "trade_123"
    acc_id = uuid.uuid4()
    fund_id = uuid.uuid4()
    
    trade = MagicMock(spec=Trade)
    trade.trade_id = trade_id
    trade.broker_account_id = acc_id
    trade.metadata_json = {"oanda_id": "oanda_123"}
    
    account = MagicMock(spec=BrokerAccount)
    account.id = acc_id
    account.fund_id = fund_id
    account.credentials_encrypted = "enc"
    
    # Permission check mock
    user_fund = MagicMock(spec=UserFund)
    
    def side_effect_query(model):
        q = MagicMock()
        if model == Trade:
             q.filter.return_value.first.return_value = trade
        elif model == BrokerAccount:
             q.filter.return_value.first.return_value = account
        elif model == UserFund:
            q.join.return_value.filter.return_value.first.return_value = user_fund
        return q
    local_mock_db.query.side_effect = side_effect_query
    
    with patch("app.routers.execution.execution_client.close_trade", new_callable=AsyncMock) as mock_close:
         with patch("app.routers.execution.decrypt_data", return_value={"api_key": "k", "account_id": "a"}):
             with patch("app.routers.execution.TradeService.close_trade") as mock_service_close:
                 mock_closed_trade = MagicMock()
                 mock_closed_trade.trade_id = trade_id
                 mock_closed_trade.pnl_usd = 50.0
                 mock_closed_trade.exit_price = 2010.0
                 mock_service_close.return_value = mock_closed_trade
                 
                 response = client.post(f"/api/v1/execution/trades/{trade_id}/close", json={"exit_price": 2010.0})
                 
                 assert response.status_code == 200
                 assert response.json()["data"]["pnl"] == 50.0
                 
                 mock_close.assert_called_once() # Verify call to broker

@pytest.mark.asyncio
async def test_place_smart_order(client, local_mock_db, mock_user):
    acc_id = uuid.uuid4()
    acc = MagicMock(spec=BrokerAccount)
    acc.id = acc_id
    
    # Mock permission check: join(Fund).join(UserFund).filter(...) returns account
    local_mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.first.return_value = acc
    
    payload = {
        "broker_account_id": str(acc_id),
        "symbol": "EUR/USD",
        "direction": "BULLISH",
        "risk_usd": 100.0
    }
    
    with patch("app.routers.execution.execution_client.place_smart_order", new_callable=AsyncMock) as mock_smart:
        mock_smart.return_value = {"id": "smart_1", "price": 1.1}
        
        with patch("app.routers.execution.TradeService.create_trade_from_execution") as mock_create:
            mock_trade = MagicMock()
            mock_create.return_value = mock_trade
            
            response = client.post("/api/v1/execution/smart-orders", json=payload)
            assert response.status_code == 200
            assert response.json()["data"]["id"] == "smart_1"
            
            mock_create.assert_called_once()
