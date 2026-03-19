
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.adapters.ctrader import CTraderOrderAdapter

@pytest.fixture
def mock_ctrader_client():
    client = AsyncMock()
    return client

@pytest.mark.asyncio
@patch("app.adapters.ctrader.CTraderConnectionManager")
async def test_ctrader_cancel_order(mock_manager, mock_ctrader_client):
    # Setup
    mock_manager.get_client.return_value = mock_ctrader_client
    adapter = CTraderOrderAdapter("id", "secret", "123", "token")
    
    mock_ctrader_client.cancel_order.return_value = {"status": "cancelled"}
    
    # Test
    res = await adapter.cancel_order("555")
    
    assert res["status"] == "cancelled"
    assert res["order_id"] == "555"
    mock_ctrader_client.cancel_order.assert_called_with(123, 555)

@pytest.mark.asyncio
@patch("app.adapters.ctrader.CTraderConnectionManager")
@patch("app.adapters.ctrader.CTraderOrderAdapter._resolve_symbol_id_and_lot_size")
async def test_ctrader_get_pending_orders(mock_resolve, mock_manager, mock_ctrader_client):
    # Setup
    mock_manager.get_client.return_value = mock_ctrader_client
    adapter = CTraderOrderAdapter("id", "secret", "123", "token")
    mock_resolve.return_value = (1, 100000) # Mock L3 Cache resolve for symbolId=1
    
    # Mock Reconcile Response
    mock_reconcile = MagicMock()
    
    # Mock Order 1
    o1 = MagicMock()
    o1.orderId = 101
    o1.tradeData.symbolId = 1
    o1.tradeData.volume = 100000 # 1000 units (cents/100) -> 1000.0? No, units = vol/100. 100000/100 = 1000.
    o1.orderType = 2 # LIMIT
    o1.limitPrice = 1.0500
    o1.stopPrice = 0.0
    o1.tradeData.openTimestamp = 1600000000000
    
    mock_reconcile.order = [o1]
    mock_ctrader_client.get_reconcile.return_value = mock_reconcile
    
    # Test
    orders = await adapter.get_pending_orders()
    
    assert len(orders) == 1
    assert orders[0]["id"] == "101"
    assert orders[0]["units"] == 1000.0
    assert orders[0]["price"] == 1.0500
