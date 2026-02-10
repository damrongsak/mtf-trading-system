import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.order_service import OrderService
from app.models import BrokerAccount, Fund

@pytest.mark.asyncio
async def test_execute_smart_order_oanda_success():
    # Setup mocks
    db = AsyncMock()
    mock_account = MagicMock(spec=BrokerAccount)
    mock_account.broker_name = "OANDA"
    mock_account.supported_symbols = ["XAU_USD"]
    
    mock_fund = MagicMock(spec=Fund)
    mock_fund.risk_percentage = 0.01
    mock_fund.max_risk_per_trade = 1000.0
    
    mock_account.risk_settings = None # Ensure no account limit
    
    # Mock DB queries
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.side_effect = [mock_account, mock_fund]
    db.execute.return_value = mock_result
    
    order_data = {
        "broker_account_id": str(uuid.uuid4()),
        "symbol": "XAU_USD",
        "direction": "BULLISH",
        "stop_loss": 2000.0,
        "risk_usd": 100.0
    }
    
    with patch("app.services.order_service.BrokerFactory") as mock_factory, \
         patch("app.services.order_service.decrypt_data") as mock_decrypt, \
         patch("app.services.order_service.MinimaxService") as mock_minimax:
        
        mock_adapter = AsyncMock()
        mock_factory.get_adapter.return_value = mock_adapter
        mock_adapter.get_current_price.return_value = 2010.0
        mock_adapter.get_account_summary.return_value = {"NAV": "10000"}
        mock_adapter.place_market_order.return_value = {"orderFillTransaction": {"id": "oanda_123"}}
        mock_decrypt.return_value = {"api_key": "test"}
        mock_minimax.calculate_regret.return_value = (True, 0.0, "OK")
        
        result = await OrderService.execute_smart_order(order_data, db)
        
        assert result["id"] == "oanda_123"
        mock_adapter.place_market_order.assert_called_once()

@pytest.mark.asyncio
async def test_execute_smart_order_invalid_uuid():
    db = AsyncMock()
    order_data = {"broker_account_id": "not-a-uuid"}
    with pytest.raises(ValueError, match="Invalid UUID format"):
        await OrderService.execute_smart_order(order_data, db)

@pytest.mark.asyncio
async def test_execute_smart_order_account_not_found():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    db.execute.return_value = mock_result
    
    order_data = {"broker_account_id": str(uuid.uuid4())}
    with pytest.raises(ValueError, match="Broker Account not found"):
        await OrderService.execute_smart_order(order_data, db)

@pytest.mark.asyncio
async def test_execute_smart_order_inactive_account():
    db = AsyncMock()
    mock_account = MagicMock(spec=BrokerAccount)
    mock_account.is_active = False
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_account
    db.execute.return_value = mock_result
    
    order_data = {"broker_account_id": str(uuid.uuid4())}
    with pytest.raises(ValueError, match="Broker Account is inactive"):
        await OrderService.execute_smart_order(order_data, db)
