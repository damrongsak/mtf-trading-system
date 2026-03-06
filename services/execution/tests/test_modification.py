"""
Tests: amend_order and amend_position for cTrader

SAFETY: No real broker connections. Client & symbol cache are fully mocked.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.adapters.ctrader import CTraderOrderAdapter


@pytest.mark.asyncio
async def test_ctrader_amend_order():
    """
    [SAFETY] amend_order should correctly compute the volume in cTrader cents
    from universal units and call the broker with the right parameters.
    A wrong volume here would directly affect a live position size.
    """
    adapter = CTraderOrderAdapter("id", "secret", "123", "token")
    adapter.client = AsyncMock()
    # Pre-populate L3 cache: XAUUSD, lotSize=10000 cents
    adapter._symbol_cache["XAUUSD"] = (93, 10000)
    adapter._symbol_cache["ID_93"] = ("XAUUSD", 10000)

    # Mock get_pending_orders to provide target order state
    adapter.get_pending_orders = AsyncMock(return_value=[
        {"id": "555", "instrument": "XAUUSD", "units": 1000.0, "raw_volume": 100, "price": 2045.0}
    ])

    # Amend: Change units to 2000 (0.02 lot of Gold) and price to 2350.0
    await adapter.amend_order(order_id="555", units=2000.0, price=2350.0)

    # Verify client call:
    # (2000 / 100000) * 10000 = 200 cTrader cents
    call_args = adapter.client.amend_order.call_args[1]
    assert call_args["order_id"] == 555
    assert call_args["volume"] == 200
    assert call_args["price"] == 2350.0


@pytest.mark.asyncio
async def test_ctrader_amend_position_success():
    """
    [SAFETY] amend_position should call broker with the correct SL/TP values.
    """
    adapter = CTraderOrderAdapter("id", "secret", "123", "token")
    adapter.client = AsyncMock()

    # Mock get_reconcile -> Return a LONG position at entry=2000.0
    mock_reconcile = MagicMock()
    mock_pos = MagicMock()
    mock_pos.positionId = 777
    from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATradeSide
    mock_pos.tradeData.tradeSide = ProtoOATradeSide.BUY
    mock_pos.price = 2000.0
    mock_reconcile.position = [mock_pos]
    adapter.client.get_reconcile.return_value = mock_reconcile

    # Valid SL < Entry (2000), Valid TP > Entry
    await adapter.amend_position(broker_trade_id="777", sl_price=1900.0, tp_price=2100.0)

    call_args = adapter.client.amend_position_sltp.call_args[1]
    assert call_args["position_id"] == 777
    assert call_args["sl"] == 1900.0
    assert call_args["tp"] == 2100.0


@pytest.mark.asyncio
async def test_ctrader_amend_position_validation_long_invalid_tp():
    """
    [SAFETY] amend_position should reject TP <= entry_price for LONG positions.
    """
    from app.adapters.ctrader import RiskValidationError
    adapter = CTraderOrderAdapter("id", "secret", "123", "token")
    adapter.client = AsyncMock()

    mock_reconcile = MagicMock()
    mock_pos = MagicMock()
    mock_pos.positionId = 777
    from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATradeSide
    mock_pos.tradeData.tradeSide = ProtoOATradeSide.BUY
    mock_pos.price = 2000.0
    mock_reconcile.position = [mock_pos]
    adapter.client.get_reconcile.return_value = mock_reconcile

    with pytest.raises(RiskValidationError, match="Invalid TP for LONG"):
        # TP 1950 <= Entry 2000 (Invalid for LONG)
        await adapter.amend_position(broker_trade_id="777", sl_price=1900.0, tp_price=1950.0)


@pytest.mark.asyncio
async def test_ctrader_amend_position_validation_short_invalid_sl():
    """
    [SAFETY] amend_position should reject SL <= entry_price for SHORT positions.
    """
    from app.adapters.ctrader import RiskValidationError
    adapter = CTraderOrderAdapter("id", "secret", "123", "token")
    adapter.client = AsyncMock()

    mock_reconcile = MagicMock()
    mock_pos = MagicMock()
    mock_pos.positionId = 888
    from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATradeSide
    mock_pos.tradeData.tradeSide = ProtoOATradeSide.SELL
    mock_pos.price = 2000.0
    mock_reconcile.position = [mock_pos]
    adapter.client.get_reconcile.return_value = mock_reconcile

    with pytest.raises(RiskValidationError, match="Invalid SL for SHORT"):
        # SL 1950 <= Entry 2000 (Invalid for SHORT, SL must be > Entry)
        await adapter.amend_position(broker_trade_id="888", sl_price=1950.0, tp_price=1900.0)


@pytest.mark.asyncio
async def test_ctrader_get_current_price_success():
    """
    [SAFETY] get_current_price must return the midpoint of BID/ASK from the broker.
    """
    adapter = CTraderOrderAdapter("id", "secret", "123", "token")
    adapter.client = AsyncMock()
    adapter._symbol_cache["XAUUSD"] = (93, 10000)

    # Mock get_spot_price to return (Bid, Ask)
    adapter.client.get_spot_price.return_value = (2000.0, 2002.0)

    price = await adapter.get_current_price("XAUUSD")
    assert price == 2001.0
    adapter.client.get_spot_price.assert_called_once_with(123, 93)

@pytest.mark.asyncio
async def test_ctrader_get_current_price_zero_raises_error():
    """
    [SAFETY] get_current_price must not silently return 0.0 if fetch fails.
    """
    adapter = CTraderOrderAdapter("id", "secret", "123", "token")
    adapter.client = AsyncMock()
    adapter._symbol_cache["XAUUSD"] = (93, 10000)

    adapter.client.get_spot_price.return_value = (0.0, 0.0)

    with pytest.raises(ValueError, match="zero prices"):
        await adapter.get_current_price("XAUUSD")

@pytest.mark.asyncio
async def test_oanda_amend_order_success():
    """
    [SAFETY] OANDA amend_order must fetch the existing order and send an OrderReplace request with SL/TP.
    """
    from app.adapters.oanda_order import OandaOrderAdapter
    adapter = OandaOrderAdapter("id", "123")
    adapter.client = MagicMock()
    
    def mock_request(r):
        r.response = {"orderCreateTransaction": {"id": "556"}}
        return r.response
        
    adapter.client.request = MagicMock(side_effect=mock_request)

    # Mock get_pending_orders 
    adapter.get_pending_orders = AsyncMock(return_value=[
        {"id": "555", "instrument": "XAU_USD", "units": "100", "type": "LIMIT", "price": "2000.000"}
    ])

    result = await adapter.amend_order(order_id="555", units=200, price=2100.0, sl_price=2050.0)
    assert result["order_id"] == "556"

    # Verify OANDA API request
    call_args = adapter.client.request.call_args[0][0] # The OrderReplace object
    assert call_args.__class__.__name__ == "OrderReplace"
    data = call_args.data["order"]
    assert data["units"] == "200.0"
    assert data["price"] == "2100.0"
    assert data["stopLossOnFill"]["price"] == "2050.0"


@pytest.mark.asyncio
async def test_oanda_amend_position_success():
    """
    [SAFETY] OANDA amend_position must utilize TradeCRCDO with correct SL/TP format.
    """
    from app.adapters.oanda_order import OandaOrderAdapter
    adapter = OandaOrderAdapter("id", "123")
    adapter.client = MagicMock()
    adapter.client.request = MagicMock()

    await adapter.amend_position(broker_trade_id="777", sl_price=1900.0, tp_price=2200.0)

    call_args = adapter.client.request.call_args[0][0] # The TradeCRCDO object
    assert call_args.__class__.__name__ == "TradeCRCDO"
    data = call_args.data
    assert data["stopLoss"]["price"] == "1900.0"
    assert data["takeProfit"]["price"] == "2200.0"

