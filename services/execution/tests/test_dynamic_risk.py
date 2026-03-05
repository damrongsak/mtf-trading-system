import pytest
import uuid
from unittest.mock import MagicMock, patch, AsyncMock
from app.main import app
from app.models import BrokerAccount, Fund

@pytest.fixture
def override_price():
    """Setup price service mock."""
    with patch("app.services.order_service.price_service") as mock_price:
        mock_price.get_latest_price = AsyncMock(return_value=(2000.0, None))
        yield mock_price

@patch("app.services.order_service.BrokerFactory")
@patch("app.services.order_service.decrypt_data")
@patch("app.services.order_service.MinimaxService")
def test_place_smart_order_dynamic_risk(mock_minimax, mock_decrypt, mock_factory, test_client, mock_db, override_price):
    mock_adapter = MagicMock()
    mock_factory.get_adapter.return_value = mock_adapter
    mock_decrypt.return_value = {"api_key": "test"}
    mock_minimax.calculate_regret.return_value = (True, 0.0, "OK")
    
    account_id = uuid.uuid4()
    fund_id = uuid.uuid4()
    
    mock_account = BrokerAccount(
        id=account_id,
        is_active=True,
        broker_name="OANDA",
        credentials_encrypted=b"test",
        account_number="001",
        fund_id=fund_id,
        risk_settings={},
        environment="practice",
        supported_symbols=["XAU_USD"]
    )

    mock_fund = Fund(
        id=fund_id,
        max_risk_per_trade=500.0,
        risk_percentage=0.01,
        max_drawdown_threshold=0.0,
        asset_classes=["Forex"],
        strategy_type="SMC",
        default_lot_size=0.01
    )
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.side_effect = [mock_account, mock_fund, mock_account]
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar.return_value = 0.0
    mock_db.execute.return_value = mock_result
    
    mock_adapter.get_account_summary = AsyncMock(return_value={"NAV": "10000.0"})
    mock_adapter.get_current_price = AsyncMock(return_value=2000.0)
    mock_adapter.place_market_order = AsyncMock(return_value={"orderFillTransaction": {"id": "1", "units": "10"}})
    
    payload = {
        "broker_account_id": str(account_id),
        "symbol": "XAU_USD",
        "direction": "BULLISH",
        "stop_loss": 1990.0,
        "generated_by": "test"
    }
    
    response = test_client.post("/smart-orders", json=payload, headers={"X-Internal-API-Key": "test-key"})
    
    assert response.status_code == 200, f"Response: {response.text}"
    mock_adapter.place_market_order.assert_called()
Line: 83
