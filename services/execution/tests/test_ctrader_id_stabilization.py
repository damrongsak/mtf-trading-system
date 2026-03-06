"""
Phase 15 Verification: cTrader ID Stabilization & Duplicate Fixes

Tests:
1. place_market_order correctly filters executionType (only FILLED publishes).
2. place_market_order prioritizes positionId over orderId.
3. get_open_trades includes both positions and accepted orders.
4. publish_fill includes deal_id.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from app.adapters.ctrader import CTraderOrderAdapter
from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAExecutionEvent, ProtoOAReconcileRes
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATradeSide, ProtoOAOrderStatus, ProtoOAExecutionType

@pytest.fixture
def adapter():
    a = CTraderOrderAdapter(
        client_id="test_id",
        client_secret="test_secret",
        account_id="12345",
        token="test_token"
    )
    a.client = AsyncMock()
    a.client.connect = AsyncMock()
    a.client.authorize_app = AsyncMock()
    a.client.authorize_account = AsyncMock()
    # Mock symbol resolution
    a._resolve_symbol_id_and_lot_size = AsyncMock(return_value=(1001, 10000))
    a._resolve_symbol_name = AsyncMock(return_value="XAU/USD")
    return a

@pytest.mark.asyncio
async def test_market_order_skips_accepted_event(adapter):
    """Verify that ORDER_ACCEPTED does NOT trigger publish_fill."""
    mock_res = MagicMock(spec=ProtoOAExecutionEvent)
    mock_res.payloadType = ProtoOAExecutionEvent().payloadType
    mock_res.executionType = ProtoOAExecutionType.ORDER_ACCEPTED
    mock_res.order.orderId = 111
    mock_res.HasField.side_effect = lambda f: f == "order"
    
    adapter.client.create_order.return_value = mock_res
    
    with patch("app.services.fill_publisher.publish_fill", new_callable=AsyncMock) as mock_pub:
        await adapter.place_market_order("XAU/USD", 1, trade_id="T1")
        # Should NOT be called for ORDER_ACCEPTED
        mock_pub.assert_not_called()

@pytest.mark.asyncio
async def test_market_order_publishes_on_filled(adapter):
    """Verify that ORDER_FILLED triggers publish_fill with positionId and dealId."""
    mock_res = MagicMock(spec=ProtoOAExecutionEvent)
    mock_res.payloadType = ProtoOAExecutionEvent().payloadType
    mock_res.executionType = ProtoOAExecutionType.ORDER_FILLED
    mock_res.order.orderId = 111
    mock_res.position.positionId = 222
    mock_res.deal.dealId = 333
    mock_res.deal.executionPrice = 2000.0
    mock_res.HasField.side_effect = lambda f: f in ["order", "position", "deal"]
    
    adapter.client.create_order.return_value = mock_res
    
    with patch("app.services.fill_publisher.publish_fill", new_callable=AsyncMock) as mock_pub:
        # We need to mock asyncio.create_task or wait for it
        # Simplest: mock the whole module import or use a wrapper
        with patch("asyncio.create_task", side_effect=lambda coro: coro):
             await adapter.place_market_order("XAU/USD", 1, trade_id="T1")
             
             mock_pub.assert_called_once()
             args = mock_pub.call_args.kwargs
             assert args["order_id"] == "222" # Should be positionId
             assert args["deal_id"] == "333" # Should include dealId
             assert args["status"] == "FILLED"

@pytest.mark.asyncio
async def test_reconcile_includes_orders_and_positions(adapter):
    """Verify get_open_trades returns both Positions and Pending Orders."""
    mock_reconcile = MagicMock(spec=ProtoOAReconcileRes)
    
    # Mock 1 Position
    pos = MagicMock()
    pos.positionId = 444
    pos.tradeData.symbolId = 1001
    pos.tradeData.volume = 1000 # 10 units
    pos.tradeData.tradeSide = ProtoOATradeSide.BUY
    pos.price = 1950.0
    pos.swap = 100
    pos.commission = 50
    pos.HasField.return_value = False # No SL/TP
    
    # Mock 1 Pending Order
    ord = MagicMock()
    ord.orderId = 555
    ord.orderStatus = ProtoOAOrderStatus.ORDER_STATUS_ACCEPTED
    ord.tradeData.symbolId = 1001
    ord.tradeData.volume = 500 # 5 units
    ord.tradeData.tradeSide = ProtoOATradeSide.SELL
    ord.limitPrice = 2050.0
    ord.HasField.side_effect = lambda f: f == "limitPrice"
    
    mock_reconcile.position = [pos]
    mock_reconcile.order = [ord]
    
    adapter.client.get_reconcile.return_value = mock_reconcile
    
    trades = await adapter.get_open_trades()
    
    assert len(trades) == 2
    # Check Position
    p_trade = next(t for t in trades if t["type"] == "POSITION")
    assert p_trade["id"] == "444"
    assert p_trade["units"] == 10.0
    
    # Check Order
    o_trade = next(t for t in trades if t["type"] == "ORDER")
    assert o_trade["id"] == "555"
    assert o_trade["units"] == 5.0
    assert o_trade["status"] == "PENDING"
