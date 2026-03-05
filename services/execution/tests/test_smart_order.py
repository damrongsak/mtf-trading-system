from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
import uuid
from app.main import app
from app.models import BrokerAccount, Fund

@pytest.fixture
def override_price():
    """Setup price service mock."""
    with patch("app.services.order_service.price_service") as mock_price:
        mock_price.get_latest_price = AsyncMock(return_value=(0.7000, None))
        yield mock_price

@patch("app.services.order_service.BrokerFactory")
@patch("app.services.order_service.decrypt_data")
@patch("app.services.order_service.MinimaxService")
def test_place_smart_order_dynamic_risk(mock_minimax, mock_decrypt, mock_factory, test_client, mock_db, override_price):
    # 1. Setup Mocks
    mock_adapter = MagicMock()
    mock_factory.get_adapter.return_value = mock_adapter
    mock_decrypt.return_value = {"api_key": "xyz", "account_id": "123"}
    mock_minimax.calculate_regret.return_value = (True, 0.0, "OK")
    
    account_id = uuid.uuid4()
    mock_account = BrokerAccount(
        id=account_id,
        is_active=True,
        broker_name="OANDA",
        credentials_encrypted=b"encrypted",
        account_number="123",
        environment="practice",
        fund_id=uuid.uuid4(),
        supported_symbols=["AUD_USD"]
    )
    
    mock_fund = Fund(
        id=mock_account.fund_id,
        max_risk_per_trade=100.0,
        risk_percentage=0.01,
        asset_classes=["Forex"],
        default_lot_size=0.01,
        max_drawdown_threshold=0.0
    )
    
    # 2. Mock DB Queries
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.side_effect = [mock_account, mock_fund, mock_account]
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar.return_value = 0.0
    mock_db.execute.return_value = mock_result
    
    # Adapter response
    mock_adapter.get_account_summary = AsyncMock(return_value={"NAV": "10000"})
    mock_adapter.place_market_order = AsyncMock(return_value={"orderFillTransaction": {"id": "555"}})
    
    payload = {
        "broker_account_id": str(account_id),
        "symbol": "AUD_USD",
        "direction": "BULLISH",
        "stop_loss": 0.6000, 
        "risk_usd": 1.0,    
        "generated_by": "TestStrategy",
        "reason": "Unit Test",
        "signal_id": "sig-1"
    }
    
    response = test_client.post("/smart-orders", json=payload, headers={"X-Internal-API-Key": "test-key"})
    
    assert response.status_code == 200, f"Response: {response.text}"
    resp_json = response.json()
    assert resp_json["data"]["id"] == "555"
    mock_adapter.place_market_order.assert_called_once()

@patch("app.services.order_service.BrokerFactory")
@patch("app.services.order_service.decrypt_data")
def test_place_smart_order_default_risk(mock_decrypt, mock_factory, test_client, mock_db, override_price):
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
        environment="practice",
        fund_id=uuid.uuid4(),
        supported_symbols=["AUD_USD"]
    )
    
    mock_fund = Fund(
        id=mock_account.fund_id,
        max_risk_per_trade=10.0,
        risk_percentage=0.01,
        asset_classes=["Forex"],
        default_lot_size=0.01,
        max_drawdown_threshold=0.0
    )
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.side_effect = [mock_account, mock_fund, mock_account]
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar.return_value = 0.0
    mock_db.execute.return_value = mock_result
    
    mock_adapter.get_account_summary = AsyncMock(return_value={"NAV": "1000"})
    mock_adapter.place_market_order = AsyncMock(return_value={"orderFillTransaction": {"id": "666"}})
    
    payload = {
        "broker_account_id": str(account_id),
        "symbol": "AUD_USD",
        "direction": "BULLISH",
        "stop_loss": 0.6000,
        "generated_by": "TestStrategy",
        "signal_id": "sig-2"
    }
    
    response = test_client.post("/smart-orders", json=payload, headers={"X-Internal-API-Key": "test-key"})
    assert response.status_code == 200, f"Response: {response.text}"
    
@patch("app.services.order_service.BrokerFactory")
@patch("app.services.order_service.decrypt_data")
def test_place_smart_order_price_fail(mock_decrypt, mock_factory, test_client, mock_db, override_price):
    mock_adapter = MagicMock()
    mock_factory.get_adapter.return_value = mock_adapter
    mock_decrypt.return_value = {"api_key": "xyz", "account_id": "123"}

    # Mock Price Fetch Failure (Cache and API)
    override_price.get_latest_price = AsyncMock(return_value=(0.0, "Service Down"))
    mock_adapter.get_current_price = AsyncMock(side_effect=Exception("API Error"))
    mock_adapter.get_account_summary = AsyncMock(return_value={"NAV": "1000"})

    account_id = uuid.uuid4()
    mock_account = BrokerAccount(
        id=account_id,
        is_active=True,
        broker_name="OANDA",
        credentials_encrypted=b"encrypted",
        account_number="123",
        environment="practice",
        fund_id=uuid.uuid4(),
        supported_symbols=["AUD_USD"]
    )
    
    mock_fund = Fund(
        id=mock_account.fund_id,
        max_risk_per_trade=10.0,
        asset_classes=["Forex"],
        default_lot_size=0.01,
        max_drawdown_threshold=0.0
    )
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.side_effect = [mock_account, mock_fund]
    mock_db.execute.return_value = mock_result
    
    payload = {
        "broker_account_id": str(account_id),
        "symbol": "AUD_USD",
        "direction": "BULLISH",
        "stop_loss": 0.6000,
        "generated_by": "TestStrategy",
        "reason": "Fail Test",
        "signal_id": "sig-3"
    }
    
    response = test_client.post("/smart-orders", json=payload, headers={"X-Internal-API-Key": "test-key"})
    assert response.status_code == 500
