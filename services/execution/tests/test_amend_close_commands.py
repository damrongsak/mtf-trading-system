"""
Unit Tests: amend_order, close_trade, and ORDER_NOT_FOUND Safety Mapping

SAFETY NOTICE:
    - All tests use unittest.mock (AsyncMock/MagicMock).
    - NO real broker connections are made.
    - NO real trades are placed, amended, or closed.
    - We patch `self.client` directly on the adapter to avoid any real cTrader
      auth attempts, ensuring zero risk to the live account.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# --- Fixtures ---

@pytest.fixture
def mock_client():
    """Mock cTrader client with required async methods."""
    client = AsyncMock()
    client.connect = AsyncMock()
    client.authorize_app = AsyncMock()
    client.authorize_account = AsyncMock()
    return client


@pytest.fixture
def adapter(mock_client):
    """
    Returns a CTraderOrderAdapter with:
    - self.client patched to the mock (no real cTrader connection)
    - L3 symbol cache pre-hydrated (no DB call needed)
    """
    from app.adapters.ctrader import CTraderOrderAdapter
    a = CTraderOrderAdapter("test_client_id", "test_secret", "12345", "test_token")
    a.client = mock_client  # Patch directly — 100% safe, no real connection
    # Pre-populate L3 cache directly to avoid DB dependency in unit tests
    a._symbol_cache["XAU_USD"] = (1, 10000000)  # ID=1, LotSize=10M (standard gold)
    a._symbol_cache["ID_1"] = ("XAU_USD", 10000000)
    return a


# ─────────────────────────────────────────────────────────────────────────────
# amend_order Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_amend_order_success(adapter, mock_client):
    """
    [SAFETY] amend_order should succeed and return status='amended'
    when the broker acknowledges the modification.
    The mock ensures no real LIMIT order is modified on the live account.
    """
    # Mock get_pending_orders response (returns current order state)
    mock_order_in_cache = {
        "id": "999", "instrument": "XAU_USD",
        "units": 0.01, "raw_volume": 1000, "price": 2045.0
    }
    with patch.object(adapter, "get_pending_orders", return_value=[mock_order_in_cache]):
        mock_client.amend_order.return_value = MagicMock()

        result = await adapter.amend_order(
            order_id="999",
            sl_price=2040.0,
            tp_price=2080.0
        )

    assert result["status"] == "amended"
    assert result["order_id"] == "999"
    mock_client.amend_order.assert_called_once()


@pytest.mark.asyncio
async def test_amend_order_not_found_raises_404_mapped_value_error(adapter, mock_client):
    """
    [SAFETY] amend_order should raise ValueError when ORDER_NOT_FOUND is returned.
    This maps to HTTP 404 — preventing a silent 500 error that could
    mask a double-execution attempt in live trading.
    """
    # Simulate broker returning ORDER_NOT_FOUND
    mock_client.amend_order.side_effect = Exception("Error: ORDER_NOT_FOUND for orderId=999")

    mock_order = {"id": "999", "instrument": "XAU_USD", "units": 0.01, "raw_volume": 1000, "price": 2045.0}
    with patch.object(adapter, "get_pending_orders", return_value=[mock_order]):
        with pytest.raises(ValueError, match="999"):
            await adapter.amend_order(order_id="999", sl_price=2040.0)


@pytest.mark.asyncio
async def test_amend_order_missing_from_pending_raises_value_error(adapter, mock_client):
    """
    [SAFETY] amend_order should raise ValueError if the order is not in the pending
    order list at all — preventing a silent no-op or misrouted amendment.
    """
    with patch.object(adapter, "get_pending_orders", return_value=[]):  # Empty — order gone
        with pytest.raises(ValueError, match="not found"):
            await adapter.amend_order(order_id="999", sl_price=2040.0)


@pytest.mark.asyncio
async def test_amend_order_other_exception_bubbles(adapter, mock_client):
    """
    [SAFETY] Non-ORDER_NOT_FOUND errors (e.g., network timeout) should re-raise
    without modification so callers can distinguish between 404 and 500.
    """
    mock_client.amend_order.side_effect = Exception("CONNECTION_TIMEOUT")
    mock_order = {"id": "999", "instrument": "XAU_USD", "units": 0.01, "raw_volume": 1000, "price": 2045.0}
    with patch.object(adapter, "get_pending_orders", return_value=[mock_order]):
        with pytest.raises(Exception, match="CONNECTION_TIMEOUT"):
            await adapter.amend_order(order_id="999", sl_price=2040.0)


# ─────────────────────────────────────────────────────────────────────────────
# close_trade Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_close_trade_full_close_success(adapter, mock_client):
    """
    [SAFETY] close_trade should fully close a position when units is None.
    The adapter must first fetch the position to get the full volume.
    No real position is closed — the client is fully mocked.
    """
    # Mock get_reconcile to return a position with volume
    mock_position = MagicMock()
    mock_position.positionId = 777
    mock_position.volume = 1000000  # 10,000 cents = about 0.1 standard lots
    mock_reconcile = MagicMock()
    mock_reconcile.position = [mock_position]
    mock_client.get_reconcile.return_value = mock_reconcile
    mock_client.close_position.return_value = MagicMock()

    result = await adapter.close_trade(broker_trade_id="777", units=None)

    assert result["status"] == "closed"
    assert result["trade_id"] == "777"
    mock_client.close_position.assert_called_once_with(12345, 777, volume=1000000)


@pytest.mark.asyncio
async def test_close_trade_position_not_found_raises_value_error(adapter, mock_client):
    """
    [SAFETY] close_trade should raise ValueError when the position ID doesn't exist.
    This prevents a silent failure where a 'close' was issued but the position
    was already closed — maps correctly to HTTP 404 for the caller.
    """
    mock_reconcile = MagicMock()
    mock_reconcile.position = []  # No open positions
    mock_client.get_reconcile.return_value = mock_reconcile

    with pytest.raises(ValueError, match="Position not found"):
        await adapter.close_trade(broker_trade_id="777", units=None)


# ─────────────────────────────────────────────────────────────────────────────
# L3 Symbol Cache Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_symbol_cache_forward_lookup(adapter):
    """
    [SAFETY] The L3 cache must resolve a known symbol to (ID, LotSize) in O(1).
    A cache miss here would cause a DB query blocking the execution path.
    """
    result = adapter._resolve_symbol_from_cache("XAU_USD")
    assert result == (1, 10000000)


def test_symbol_cache_reverse_lookup(adapter):
    """
    [SAFETY] The reverse cache (ID → Name) must work to display correct
    symbol names in trade lists. 'Unknown_<id>' in logs could hide risk events.
    """
    name, lot_size = adapter._resolve_name_from_id_cache(1)
    assert name == "XAU_USD"
    assert lot_size == 10000000


def test_symbol_cache_graceful_miss(adapter):
    """
    [SAFETY] A cache miss on an unknown ID must NOT raise an exception.
    The system must always be able to show trade data, even for unsupported symbols.
    """
    name, lot_size = adapter._resolve_name_from_id_cache(99999)
    assert name.startswith("Unknown_")
    assert lot_size == 10000000  # Conservative fallback lot size
