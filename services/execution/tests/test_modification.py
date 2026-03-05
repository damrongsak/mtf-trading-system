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
async def test_ctrader_amend_position():
    """
    [SAFETY] amend_position should call broker with the correct SL/TP values.
    Incorrect SL/TP in live trading exposes the account to uncontrolled risk.
    """
    adapter = CTraderOrderAdapter("id", "secret", "123", "token")
    adapter.client = AsyncMock()

    await adapter.amend_position(broker_trade_id="777", sl_price=2300.0, tp_price=2400.0)

    call_args = adapter.client.amend_position_sltp.call_args[1]
    assert call_args["position_id"] == 777
    assert call_args["sl"] == 2300.0
    assert call_args["tp"] == 2400.0
