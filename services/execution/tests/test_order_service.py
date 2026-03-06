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
    mock_fund.max_drawdown_threshold = 0.0
    mock_fund.is_enabled = True
    
    mock_account.risk_settings = None # Ensure no account limit
    
    # Mock DB queries
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.side_effect = [mock_account, mock_fund, mock_account]
    mock_result.scalars.return_value.all.return_value = [] # No active filters
    mock_result.scalar.return_value = 0.0 # For RiskLimitsAgent check_limits
    db.execute.return_value = mock_result
    
    order_data = {
        "broker_account_id": str(uuid.uuid4()),
        "symbol": "XAU_USD",
        "direction": "BULLISH",
        "stop_loss": 2000.0,
        "risk_usd": 100.0,
        "generated_by": "TestStrategy",
        "signal_id": "sig-123"
    }
    
    with patch("app.utils.redis_client.get_redis_client") as mock_redis_factory, \
         patch("app.services.order_service.BrokerFactory") as mock_factory, \
         patch("app.services.order_service.decrypt_data") as mock_decrypt, \
         patch("app.services.order_service.MinimaxService") as mock_minimax, \
         patch("app.services.order_service.RiskLimitsAgent") as mock_risk_agent:
        
        mock_rc = AsyncMock()
        mock_rc.get = AsyncMock(return_value=None)
        mock_redis_factory.return_value = mock_rc

        mock_risk_agent.check_order_size = AsyncMock(return_value=True)
        # We must also mock check_limits because it is appended to `tasks` for asyncio.gather
        mock_risk_agent.check_limits = AsyncMock(return_value=True)

        mock_adapter = AsyncMock()
        mock_factory.get_adapter.return_value = mock_adapter
        mock_adapter.get_current_price.return_value = 2010.0
        mock_adapter.get_account_summary.return_value = {"NAV": "10000"}
        mock_adapter.place_market_order.return_value = {"orderFillTransaction": {"id": "oanda_123"}}
        mock_decrypt.return_value = {"api_key": "test"}
        mock_minimax.calculate_regret.return_value = (True, 0.0, "OK")
        
        # We must specifically mock get_current_price on the service level if it's falling back
        # Wait, the error shows "Price cache miss or stale... Falling back to API." and then fails inside adapter
        # But we already mock_adapter.get_current_price.return_value = 2010.0
        # Ah, the OrderService uses `adapter.get_current_price(order.symbol)`
        # Let's ensure the adapter is returned correctly

        # Correct mock_account setup
        mock_account.id = uuid.UUID(order_data["broker_account_id"])
        mock_account.is_active = True
        mock_account.broker_name = "OANDA"
        mock_account.credentials_encrypted = b"test"
        mock_account.account_number = "001"
        mock_account.fund_id = uuid.uuid4()
        mock_account.risk_settings = {"max_lot_size": 10.0} # Avoid implicit fallback guardrails
        mock_account.environment = "practice"
        mock_account.supported_symbols = ["XAU_USD"]


        # Correct mock_fund setup
        mock_fund.id = mock_account.fund_id
        mock_fund.is_enabled = True
        
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
    
    with patch("app.services.order_service.execution_cache") as mock_cache:
        mock_cache.get_account = AsyncMock(return_value=None)
    
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
    
    with patch("app.services.order_service.execution_cache") as mock_cache:
        mock_cache.get_account = AsyncMock(return_value=None)
    
    order_data = {"broker_account_id": str(uuid.uuid4())}
    with pytest.raises(ValueError, match="Broker Account is inactive"):
        await OrderService.execute_smart_order(order_data, db)
