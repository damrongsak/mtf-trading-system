"""
Tests: place_market_order and place_limit_order comment/tag logic

SAFETY: No real broker connections. Client and symbol cache are fully mocked.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from app.adapters.ctrader import CTraderOrderAdapter


@pytest.fixture
def adapter():
    """Adapter with mocked client and pre-populated L3 symbol cache."""
    a = CTraderOrderAdapter(
        client_id="test_id",
        client_secret="test_secret",
        account_id="12345",
        token="test_token"
    )
    a.client = AsyncMock()
    # Pre-populate L3 cache for all symbols used in tests
    a._symbol_cache["XAU/USD"] = (1001, 10000, 100)
    a._symbol_cache["EUR/USD"] = (1002, 10000000, 100000)
    a._symbol_cache["S"] = (1001, 10000, 100)
    return a


@pytest.mark.asyncio
async def test_place_market_order_with_comment(adapter):
    """
    [SAFETY] place_market_order should forward 'comment' metadata to the broker.
    The comment field is used for trade identification/auditing in live accounts.
    """
    mock_response = MagicMock()
    mock_response.HasField.side_effect = lambda field: field in ["deal", "order"]
    mock_response.deal.positionId = 123456
    mock_response.deal.executionPrice = 1.2345
    mock_response.order.orderId = 789012
    adapter.client.create_order.return_value = mock_response

    result = await adapter.place_market_order(
        symbol="XAU/USD",
        units=1,
        comment="MarketOrderTest"
    )

    mock_response  # Just to ensure we have access to the response
    adapter.client.create_order.assert_called_once()
    call_kwargs = adapter.client.create_order.call_args.kwargs
    assert call_kwargs["comment"] == "MarketOrderTest"
    assert call_kwargs["symbol_id"] == 1001

    assert "orderFillTransaction" in result
    assert result["orderFillTransaction"]["instrument"] == "XAU/USD"
    assert result["orderFillTransaction"]["price"] == "1.2345"


@pytest.mark.asyncio
async def test_place_limit_order_with_comment(adapter):
    """
    [SAFETY] place_limit_order should forward 'comment' and 'price' to the broker.
    Incorrect price on a LIMIT order could result in unexpected fills.
    """
    mock_response = MagicMock()
    mock_response.HasField.side_effect = lambda field: field == "order"
    mock_response.order.orderId = 555555
    adapter.client.create_order.return_value = mock_response

    result = await adapter.place_limit_order(
        symbol="EUR/USD",
        units=10,
        entry_price=1.1000,
        comment="LimitOrderTest"
    )

    adapter.client.create_order.assert_called_once()
    call_kwargs = adapter.client.create_order.call_args.kwargs
    assert call_kwargs["comment"] == "LimitOrderTest"
    assert call_kwargs["price"] == 1.1000

    assert "orderCreateTransaction" in result
    assert result["orderCreateTransaction"]["id"] == "555555"
    assert result["orderCreateTransaction"]["instrument"] == "EUR/USD"


@pytest.mark.asyncio
async def test_place_order_default_comment(adapter):
    """
    [SAFETY] When no comment is provided but trade_id exists, the comment
    should default to 'Ref:<trade_id>' for auditability of live trades.
    """
    mock_response = MagicMock()
    mock_response.HasField.return_value = True
    mock_response.order.orderId = 111
    mock_response.deal.positionId = 222
    mock_response.deal.executionPrice = 1.0
    adapter.client.create_order.return_value = mock_response

    await adapter.place_market_order("S", 1, trade_id="T123")

    call_kwargs = adapter.client.create_order.call_args.kwargs
    assert call_kwargs["comment"] == "Ref:T123"


@pytest.mark.asyncio
async def test_place_order_auto_comment(adapter):
    """
    [SAFETY] Without comment or trade_id, comment should default to 'Auto'.
    Ensures all broker orders are tagged for auditability.
    """
    mock_response = MagicMock()
    mock_response.HasField.return_value = True
    mock_response.order.orderId = 111
    adapter.client.create_order.return_value = mock_response

    await adapter.place_market_order("S", 1)

    call_kwargs = adapter.client.create_order.call_args.kwargs
    assert call_kwargs["comment"] == "Auto"
