"""
Tests: Volume Normalization for cTrader (Gold & FX)

SAFETY: No real broker connections. Client & symbol cache are fully mocked.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.adapters.ctrader import CTraderOrderAdapter


@pytest.fixture
def gold_adapter():
    """Adapter pre-configured with Gold (XAUUSD) in the L3 symbol cache."""
    a = CTraderOrderAdapter("id", "secret", "123", "token")
    a.client = AsyncMock()
    a.client.create_order.return_value = MagicMock()
    # Gold: 1 standard lot = 100oz. lotSize=10000 cents, step=100 cents (1oz)
    a._symbol_cache["XAUUSD"] = (93, 10000, 100)
    a._symbol_cache["ID_93"] = ("XAUUSD", 10000, 100)
    return a


@pytest.fixture
def fx_adapter():
    """Adapter pre-configured with EURUSD in the L3 symbol cache."""
    a = CTraderOrderAdapter("id", "secret", "123", "token")
    a.client = AsyncMock()
    a.client.create_order.return_value = MagicMock()
    # FX: 1 standard lot = 100,000 units. lotSize=10,000,000 cents, step=100,000 cents (1,000 units)
    a._symbol_cache["EURUSD"] = (1, 10000000, 100000)
    a._symbol_cache["ID_1"] = ("EURUSD", 10000000, 100000)
    return a


@pytest.mark.asyncio
async def test_ctrader_volume_normalization_gold(gold_adapter):
    """
    [SAFETY] 1000 universal units of Gold should map to 100 cTrader cents.
    Verifies: (units / 100_000) * lotSize = (1000 / 100000) * 10000 = 100 cents.
    Correct volume prevents over/under-sizing a real Gold position.
    """
    units = 1000.0
    await gold_adapter.place_market_order("XAUUSD", units)

    call_args = gold_adapter.client.create_order.call_args[1]
    assert call_args["volume"] == 100


@pytest.mark.asyncio
async def test_ctrader_volume_normalization_fx(fx_adapter):
    """
    [SAFETY] 1000 universal units of FX (EURUSD) should map to 100,000 cTrader cents.
    Verifies: (units / 100_000) * lotSize = (1000 / 100000) * 10000000 = 100000 cents.
    Correct volume prevents over/under-sizing a live FX position.
    """
    units = 1000.0
    await fx_adapter.place_market_order("EURUSD", units)

    call_args = fx_adapter.client.create_order.call_args[1]
    assert call_args["volume"] == 100000


@pytest.mark.asyncio
async def test_ctrader_reverse_normalization():
    """
    [SAFETY] get_open_trades should correctly convert cTrader native volume
    (cents) back to universal units for consistent display.
    """
    a = CTraderOrderAdapter("id", "secret", "123", "token")
    a.client = AsyncMock()
    # Pre-populate reverse cache: XAUUSD, lotSize=10000, step=100
    a._symbol_cache["XAUUSD"] = (93, 10000, 100)
    a._symbol_cache["ID_93"] = ("XAUUSD", 10000, 100)

    mock_position = MagicMock()
    mock_position.tradeData.symbolId = 93
    mock_position.tradeData.volume = 100  # 1oz of Gold in cTrader cents
    mock_position.tradeData.tradeSide = 1  # BUY
    mock_position.positionId = 555
    mock_position.price = 2050.0
    mock_position.grossProfit = 500  # 5 USD gain

    mock_reconcile = MagicMock()
    mock_reconcile.position = [mock_position]
    a.client.get_reconcile.return_value = mock_reconcile

    trades = await a.get_open_trades()
    assert len(trades) == 1
    # 100 cents / 10,000 lotSize * 100,000 units = 1000 units
    assert trades[0]["units"] == 1000.0
