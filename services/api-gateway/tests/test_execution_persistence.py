import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.database import get_db
from app.main import app
from app.models.user_fund import User
from app.models.broker_account import BrokerAccount
from app.security import get_current_user

# --- Fixtures ---

@pytest.fixture
def mock_execution_client():
    with patch("app.routers.execution.execution_client") as mock:
        yield mock

@pytest.fixture
def mock_trade_service():
    with patch("app.routers.execution.TradeService") as mock:
        yield mock

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def client(mock_db):
    def override_get_db():
        yield mock_db
    
    def override_get_current_user():
        return User(id="123", username="testuser")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def test_user_token():
    return {"Authorization": "Bearer test-token"}

# --- Tests ---

def test_place_order_persistence(client, test_user_token, mock_execution_client, mock_trade_service, mock_db):
    """
    Test that placing an order triggers TradeService.create_trade_from_execution.
    """
    # Mock Account
    mock_account = MagicMock(spec=BrokerAccount)
    mock_account.id = "acc_123"
    mock_account.broker_name = "OANDA"
    mock_account.credentials_encrypted = "enc_creds"
    mock_account.is_active = True

    # Mock DB Queries
    def query_side_effect(model):
        mock_query = MagicMock()
        if model == BrokerAccount:
            mock_query.join.return_value.join.return_value.filter.return_value.filter.return_value.first.return_value = mock_account
            mock_query.join.return_value.join.return_value.filter.return_value.first.return_value = mock_account
            
            # Additional safety for simplier account lookup if needed
            mock_query.filter.return_value.first.return_value = mock_account
        return mock_query

    mock_db.query.side_effect = query_side_effect
    
    # Mock Execution Client Response
    mock_execution_client.place_order = AsyncMock(return_value={
        "id": "oanda_123",
        "instrument": "XAU/USD",
        "units": "1.0",
        "price": "2000.00",
        "time": "2023-01-01T12:00:00Z"
    })
    
    # Mock Trade Service Persistence
    mock_trade_service.create_trade_from_execution.return_value = MagicMock() # Return dummy trade

    # Mock _get_broker_config helper which calls decrypt_data
    with patch("app.routers.execution.decrypt_data", return_value={"api_key":"123"}):
        payload = {
            "symbol": "XAU/USD",
            "units": 1.0, 
            "sl_price": 1990.0,
            "tp_price": 2020.0
        }

        # 3. Call Endpoint
        response = client.post(
            "/api/v1/execution/orders",
            json=payload,
            headers=test_user_token
        )

    # 4. Verify Success
    if response.status_code != 200:
        print(response.json())
        
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["id"] == "oanda_123"

    # 5. Verify TradeService was called
    mock_trade_service.create_trade_from_execution.assert_called_once()
    call_args = mock_trade_service.create_trade_from_execution.call_args
    assert call_args.kwargs["user"].id == "123"
    assert call_args.kwargs["execution_data"]["id"] == "oanda_123"
    assert call_args.kwargs["request_data"]["symbol"] == "XAU/USD"


def test_close_trade_router_call(client, test_user_token, mock_db, mock_execution_client, mock_trade_service):
    """
    Test that calling close trade endpoint delegates to TradeService.close_trade.
    """
    from app.models.trade import Trade
    
    # Mock Trade
    mock_trade = MagicMock(spec=Trade)
    mock_trade.trade_id = "uuid-123"
    mock_trade.broker_account_id = None # Simplify: local close
    mock_trade.pnl_usd = 50.0
    mock_trade.exit_price = 2010.0
    
    # Mock DB
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_trade
    mock_db.query.return_value = mock_query
    
    # Mock Trade Service Response
    mock_trade_service.close_trade.return_value = mock_trade

    payload = {"exit_price": 2010.0}
    
    response = client.post(
        "/api/v1/execution/trades/uuid-123/close",
        json=payload,
        headers=test_user_token
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["trade_id"] == "uuid-123"
    
    mock_trade_service.close_trade.assert_called_once()


def test_get_open_trades(client, test_user_token, mock_db, mock_execution_client):
    """
    Test GET /execution/trades?status=OPEN with pagination
    """
    from app.models.trade import Trade, TradeStatus
    from app.models.broker_account import BrokerAccount
    from datetime import datetime
    from decimal import Decimal
    import uuid

    # 1. Mock DB Query
    mock_trade = MagicMock(spec=Trade)
    mock_trade.trade_id = uuid.uuid4()
    mock_trade.status = TradeStatus.OPEN
    mock_trade.symbol = "XAU/USD"
    mock_trade.strategy_name = "Test Strategy"
    mock_trade.signal_timestamp = datetime(2023, 1, 1, 12, 0, 0)
    mock_trade.direction = "LONG"
    mock_trade.entry_price = Decimal("2000.00")
    mock_trade.sl_price = Decimal("1990.00")
    mock_trade.tp_price = Decimal("2020.00")
    mock_trade.lot_size = Decimal("0.10")
    mock_trade.risk_usd = Decimal("5.00")
    mock_trade.created_at = datetime(2023, 1, 1, 12, 0, 0)
    mock_trade.updated_at = datetime(2023, 1, 1, 12, 0, 0)
    mock_trade.pnl_usd = Decimal("0.00")
    mock_trade.exit_price = None
    mock_trade.exit_timestamp = None
    mock_trade.rejection_reason = None
    mock_trade.metadata_json = {}
    mock_trade.strategy_run_id = None
    mock_trade.atr_pips = None
    mock_trade.rr_ratio = None
    mock_trade.mae_usd = None
    mock_trade.mfe_usd = None
    mock_trade.broker_account_id = uuid.uuid4()
    mock_trade.account = MagicMock(spec=BrokerAccount)
    mock_trade.account.broker_name = "OANDA"
    mock_trade.account.account_number = "123"
    
    # Robust Mocking
    mock_query_trade = MagicMock()
    # Chained filters/joins should return self
    mock_query_trade.join.return_value = mock_query_trade
    mock_query_trade.filter.return_value = mock_query_trade
    mock_query_trade.order_by.return_value = mock_query_trade
    mock_query_trade.offset.return_value = mock_query_trade
    mock_query_trade.limit.return_value = mock_query_trade
    
    mock_query_trade.all.return_value = [mock_trade]
    mock_query_trade.count.return_value = 1
    
    mock_query_account = MagicMock()
    mock_query_account.join.return_value.join.return_value.filter.return_value.all.return_value = [] # No accounts to sync

    def query_side_effect(model):
        if model == Trade:
            return mock_query_trade
        if model == BrokerAccount:
            return mock_query_account
        return MagicMock()

    mock_db.query.side_effect = query_side_effect

    # Mock execution client for sync
    mock_execution_client.get_open_trades = AsyncMock(return_value=[])

    # 2. Call Endpoint
    response = client.get(
        "/api/v1/execution/trades?status=OPEN",
        headers=test_user_token
    )

    # 3. Verify Response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["symbol"] == "XAU/USD"
    assert data["meta"]["total"] == 1
