
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.models import BrokerAccount
import uuid

client = TestClient(app)

from app.database import get_db

client = TestClient(app)

@pytest.fixture
def mock_db_session():
    mock_session = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_session
    yield mock_session
    app.dependency_overrides = {}

@patch("app.main.BrokerFactory")
@patch("app.main.decrypt_data")
def test_cancel_pending_orders_success(mock_decrypt, mock_factory, mock_db_session):
    # Setup Mocks
    mock_adapter = MagicMock()
    mock_factory.get_adapter.return_value = mock_adapter
    mock_decrypt.return_value = {"api_key": "xyz", "account_id": "123"}
    
    account_id = uuid.uuid4()
    mock_account = BrokerAccount(
        id=account_id,
        is_active=True,
        broker_name="OANDA",
        credentials_encrypted=b"encrypted",
        account_number="123",
        environment="practice"
    )
    
    # Mock DB Query
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_account
    mock_db_session.execute.return_value = mock_result

    # Mock Adapter Methods
    mock_adapter.get_pending_orders = AsyncMock(return_value=[
        {"id": "101", "instrument": "EUR_USD"},
        {"id": "102", "instrument": "GBP_USD"},
        {"id": "103", "instrument": "EUR_USD"}
    ])
    mock_adapter.cancel_order = AsyncMock(return_value={"orderCancelTransaction": {"id": "cancel_id"}})
    
    # Test 1: Cancel All
    response = client.delete(f"/orders?broker_account_id={str(account_id)}")
    
    assert response.status_code == 200, f"Failed with {response.status_code}: {response.text}"
    data = response.json().get("data")
    assert data["cancelled"] == 3
    assert data["errors"] == []
    
    assert mock_adapter.cancel_order.call_count == 3
    
    # Reset mocks
    mock_adapter.cancel_order.reset_mock()
    
    # Test 2: Cancel with Symbol Filter
    response_filter = client.delete(f"/orders?broker_account_id={str(account_id)}&symbol=EUR_USD")
    
    assert response_filter.status_code == 200
    data_filter = response_filter.json().get("data")
    assert data_filter["cancelled"] == 2 # Only EUR_USD
    
    assert mock_adapter.cancel_order.call_count == 2
