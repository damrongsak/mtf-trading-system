"""
Sprint F Unit Tests: Critical Safety Guards

SAFETY NOTICE:
- All tests use AsyncMock/MagicMock only.
- NO real broker connections, NO real trades.
- These tests verify that the safety guards PREVENT dangerous operations.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.adapters.ctrader import CTraderOrderAdapter, RiskValidationError


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def adapter():
    """Adapter with patched client and pre-populated L3 cache."""
    a = CTraderOrderAdapter("id", "secret", "12345", "token")
    a.client = AsyncMock()
    a._symbol_cache["XAU_USD"] = (93, 10000, 100)
    a._symbol_cache["ID_93"] = ("XAU_USD", 10000, 100)
    return a


@pytest.fixture
def long_order():
    """A realistic LONG pending order for XAU_USD at $2050."""
    return {
        "id": "555",
        "instrument": "XAU_USD",
        "units": 1.0,
        "raw_volume": 100,
        "price": 2050.0,
        "side": "BUY"
    }


@pytest.fixture
def short_order():
    """A realistic SHORT pending order for XAU_USD at $2050."""
    return {
        "id": "666",
        "instrument": "XAU_USD",
        "units": 1.0,
        "raw_volume": 100,
        "price": 2050.0,
        "side": "SELL"
    }


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3: Pre-trade Risk Validation Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_amend_sl_below_entry_for_long_passes(adapter, long_order):
    """
    [SAFETY] amend_order: SL below entry for a LONG order is VALID.
    Protects against losses by being below market.
    """
    adapter.client.amend_order.return_value = MagicMock()
    with patch.object(adapter, "get_pending_orders", return_value=[long_order]):
        result = await adapter.amend_order(
            order_id="555",
            sl_price=2030.0,  # Below entry 2050 → VALID for LONG
        )
    assert result["status"] == "amended"


@pytest.mark.asyncio
async def test_amend_sl_above_entry_for_long_raises_risk_error(adapter, long_order):
    """
    [SAFETY] amend_order: SL above entry for a LONG order is INVALID.
    A stop loss ABOVE entry means the position would NEVER be stopped out
    before you've already lost more than intended — this is a critical error.
    """
    with patch.object(adapter, "get_pending_orders", return_value=[long_order]):
        with pytest.raises(RiskValidationError, match="LONG"):
            await adapter.amend_order(
                order_id="555",
                sl_price=2060.0,  # ABOVE entry 2050 → INVALID for LONG
            )


@pytest.mark.asyncio
async def test_amend_sl_above_entry_for_short_passes(adapter, short_order):
    """
    [SAFETY] amend_order: SL above entry for a SHORT order is VALID.
    """
    adapter.client.amend_order.return_value = MagicMock()
    with patch.object(adapter, "get_pending_orders", return_value=[short_order]):
        result = await adapter.amend_order(
            order_id="666",
            sl_price=2070.0,  # Above entry 2050 → VALID for SHORT
        )
    assert result["status"] == "amended"


@pytest.mark.asyncio
async def test_amend_sl_below_entry_for_short_raises_risk_error(adapter, short_order):
    """
    [SAFETY] amend_order: SL below entry for SHORT order is INVALID.
    A stop below your short entry means you'd stop out in profit direction,
    effectively destroying your risk management.
    """
    with patch.object(adapter, "get_pending_orders", return_value=[short_order]):
        with pytest.raises(RiskValidationError, match="SHORT"):
            await adapter.amend_order(
                order_id="666",
                sl_price=2040.0,  # Below entry 2050 → INVALID for SHORT
            )


@pytest.mark.asyncio
async def test_amend_tp_above_entry_for_long_passes(adapter, long_order):
    """
    [SAFETY] amend_order: TP above entry for a LONG order is VALID.
    """
    adapter.client.amend_order.return_value = MagicMock()
    with patch.object(adapter, "get_pending_orders", return_value=[long_order]):
        result = await adapter.amend_order(
            order_id="555",
            tp_price=2100.0,  # Above entry 2050 → VALID for LONG
        )
    assert result["status"] == "amended"


@pytest.mark.asyncio
async def test_amend_tp_below_entry_for_long_raises_risk_error(adapter, long_order):
    """
    [SAFETY] amend_order: TP below entry for a LONG order is INVALID.
    Setting TP below entry means you'd exit at a guaranteed loss.
    """
    with patch.object(adapter, "get_pending_orders", return_value=[long_order]):
        with pytest.raises(RiskValidationError, match="LONG"):
            await adapter.amend_order(
                order_id="555",
                tp_price=2040.0,  # Below entry 2050 → INVALID TP for LONG
            )


@pytest.mark.asyncio
async def test_amend_no_sl_tp_skips_risk_check(adapter, long_order):
    """
    [SAFETY] amend_order: When only changing price/units (no SL/TP provided),
    the risk check is skipped. This is safe behavior.
    """
    adapter.client.amend_order.return_value = MagicMock()
    with patch.object(adapter, "get_pending_orders", return_value=[long_order]):
        result = await adapter.amend_order(
            order_id="555",
            # No sl_price, no tp_price → risk check skipped
            units=2.0,
        )
    assert result["status"] == "amended"


# End of risk validation tests. Idempotency and HMAC tests are handled in api-gateway.
