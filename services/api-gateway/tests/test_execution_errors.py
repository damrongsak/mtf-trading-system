import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.security import get_current_user
from app.models.trade import Trade, TradeDirection
from app.models.broker_account import BrokerAccount
from app.models.user_fund import User
from app.services.trade_service import TradeService
import uuid

@pytest.fixture
def local_mock_db():
    db = MagicMock()
    # Chain joins to return default query mock
    # query().join() -> query()
    # query().join().join() -> query()
    # query().filter() -> query()
    # Default query mock
    q = db.query.return_value
    q.join.return_value = q
    q.filter.return_value = q
    # Note: query(Model) returns q. 
    # But if side_effect is used elsewhere, be careful.
    return db

@pytest.fixture(autouse=True)
def override_dependency(local_mock_db):
    app.dependency_overrides[get_db] = lambda: local_mock_db
    yield
    app.dependency_overrides = {}

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = str(uuid.uuid4())
    user.username = "testuser"
    return user

@pytest.fixture
def client(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides[get_current_user] = None

def test_place_order_account_not_found(client, local_mock_db, mock_user):
    # Mock account query -> None
    # Because of chaining above: db.query().join().join().filter().first() -> q.first()
    local_mock_db.query.return_value.first.return_value = None
    
    payload = {
        "symbol": "AAPL",
        "direction": "LONG",
        "strategy_id": str(uuid.uuid4()),
        "timeframe": "1h",
        "lot_size": 0.1,
        "entry_price": 100.0,
        "risk_usd": 10.0,
        "sl_price": 99.0,
        "tp_price": 102.0
    }
    
    response = client.post("/api/v1/execution/orders", json=payload)
    if response.status_code != 404:
        print(response.json())
    assert response.status_code == 404
    assert "account not found" in response.text.lower()

def test_close_trade_not_found(client, local_mock_db, mock_user):
    # Mock trade query -> None
    local_mock_db.query.return_value.filter.return_value.first.return_value = None
    
    trade_id = str(uuid.uuid4())
    response = client.post(f"/api/v1/execution/trades/{trade_id}/close", json={"exit_price": 100.0})
    if response.status_code != 404:
        print(response.json())
    assert response.status_code == 404

def test_manual_close_trade_exception(client, local_mock_db, mock_user):
    # Mock trade query -> Trade found
    mock_trade = MagicMock(spec=Trade)
    mock_trade.trade_id = uuid.uuid4()
    mock_trade.direction = TradeDirection.LONG
    mock_trade.broker_account_id = None # Skip broker logic
    
    local_mock_db.query.return_value.filter.return_value.first.return_value = mock_trade
    
    # Mock service raising exception
    with patch("app.routers.execution.TradeService.close_trade", side_effect=ValueError("Close Failed")):
        trade_id = str(mock_trade.trade_id)
        response = client.post(f"/api/v1/execution/trades/{trade_id}/close", json={"exit_price": 100.0})
        if response.status_code != 500:
             print(response.json())
        assert response.status_code == 500
        assert "Close Failed" in response.text

def test_place_manual_order_exception(client, local_mock_db, mock_user):
    # Mock account
    mock_acc = MagicMock(spec=BrokerAccount)
    mock_acc.user_id = mock_user.id
    mock_acc.credentials_encrypted = b"enc_test" # Valid bytes
    mock_acc.broker_name = "Oanda"
    
    local_mock_db.query.return_value.filter.return_value.first.return_value = mock_acc
    
    payload = {
        "symbol": "AAPL",
        "direction": "LONG",
        "strategy_id": str(uuid.uuid4()),
        "timeframe": "1h",
        "lot_size": 0.1,
        "entry_price": 100.0,
        "risk_usd": 10.0,
        "sl_price": 99.0,
        "tp_price": 102.0,
        "account_id": str(uuid.uuid4()) # Ensure it tries to find account
    }
    
    # Mock decrypt_data too in execution router
    with patch("app.routers.execution.decrypt_data", return_value={"token": "t"}):
        # Mock ExecutionClient error
        with patch("app.routers.execution.execution_client.place_order", side_effect=ValueError("Broker Error")):
            response = client.post("/api/v1/execution/orders", json=payload)
            if response.status_code != 500:
                 print(response.json())
            assert response.status_code == 500
            assert "Broker Error" in response.text
