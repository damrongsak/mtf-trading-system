import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.database import get_db
from app.main import app
from app.models.user_fund import User
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
    # 1. Mock Execution Client Response
    mock_execution_client.place_order = AsyncMock(return_value={
        "id": "oanda_123",
        "instrument": "XAU/USD",
        "units": "1.0",
        "price": "2000.00",
        "time": "2023-01-01T12:00:00Z"
    })
    
    # 2. Mock Trade Service Persistence (to avoid actual DB/Model calls)
    mock_trade_service.create_trade_from_execution.return_value = None # Return value ignored by router

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
    assert response.status_code == 200
    assert response.json()["id"] == "oanda_123"

    # 5. Verify TradeService was called with correct data
    mock_trade_service.create_trade_from_execution.assert_called_once()
    call_args = mock_trade_service.create_trade_from_execution.call_args
    assert call_args.kwargs["user"].id == "123"
    assert call_args.kwargs["execution_data"]["id"] == "oanda_123"
    assert call_args.kwargs["request_data"]["symbol"] == "XAU/USD"


def test_close_trade_router_call(client, test_user_token, mock_trade_service):
    """
    Test that calling close trade endpoint delegates to TradeService.close_trade.
    """
    # 1. Mock Trade Service Response
    mock_trade = MagicMock()
    mock_trade.trade_id = "uuid-123"
    mock_trade.pnl_usd = 50.0
    mock_trade.exit_price = 2010.0
    
    mock_trade_service.close_trade.return_value = mock_trade

    payload = {"exit_price": 2010.0}
    
    # 3. Call Endpoint
    response = client.post(
        "/api/v1/execution/trades/uuid-123/close",
        json=payload,
        headers=test_user_token
    )

    # 3. Verify Response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["trade_id"] == "uuid-123"
    assert data["pnl"] == 50.0
    
    # 4. Verify Service Call
    mock_trade_service.close_trade.assert_called_once()
    args = mock_trade_service.close_trade.call_args
    # args[0] is db (positional), args[1] is trade_id, args[2] is exit_price
    # args[0] is db (positional), args[1] is trade_id, args[2] is exit_price
    assert args[0][1] == "uuid-123"
    assert args[0][2] == 2010.0

def test_get_open_trades(client, test_user_token, mock_db, mock_execution_client, mock_trade_service):
    """
    Test GET /execution/trades?status=OPEN with pagination
    """
    from app.models.trade import Trade, TradeStatus
    from datetime import datetime
    from decimal import Decimal

    # 1. Mock DB Query
    mock_trade = MagicMock()
    mock_trade.trade_id = "123e4567-e89b-12d3-a456-426614174000"
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
    mock_trade.pnl_usd = None
    mock_trade.exit_price = None
    mock_trade.exit_timestamp = None
    mock_trade.rejection_reason = None
    mock_trade.metadata_json = None
    mock_trade.strategy_run_id = None
    mock_trade.atr_pips = None
    mock_trade.rr_ratio = None
    mock_trade.mae_usd = None
    mock_trade.mfe_usd = None
    
    # Mock chain: query(Trade).filter(...).filter(...).order_by(...).offset(...).limit(...).all()
    # We also need to mock count()
    mock_query = mock_db.query.return_value
    mock_query.filter.return_value = mock_query # Chaining filters
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    mock_query.all.return_value = [mock_trade]
    mock_query.count.return_value = 1

    # Mock execution client for sync
    mock_execution_client.get_open_trades = AsyncMock(return_value=[])

    # 2. Call Endpoint
    response = client.get(
        "/api/v1/execution/trades?status=OPEN",
        headers=test_user_token
    )

    # 3. Verify Response
    if response.status_code != 200:
        print(f"DEBUG RESPONSE: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["symbol"] == "XAU/USD"
    
    # Verify Metadata
    assert "meta" in data
    assert data["meta"]["page"] == 1
    assert data["meta"]["per_page"] == 20
    assert data["meta"]["total"] == 1
