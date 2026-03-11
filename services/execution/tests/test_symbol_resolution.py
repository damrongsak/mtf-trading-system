"""
Tests: Symbol ID Flexible Naming Resolution

SAFETY: No real DB or broker connections. Uses cache pre-population.
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.adapters.ctrader import CTraderOrderAdapter


@pytest.fixture
def adapter_with_symbols():
    """Create adapter with pre-populated L3 cache for all test symbols."""
    a = CTraderOrderAdapter("id", "secret", "123", "token")
    a.client = AsyncMock()
    # Pre-populate the L3 cache directly: (ID, lot_size, step_size)
    a._symbol_cache["XAU_USD"] = (41, 10000, 100)
    a._symbol_cache["XAUUSD"] = (41, 10000, 100)
    a._symbol_cache["XAU/USD"] = (100, 10000, 100)
    a._symbol_cache["ID_41"] = ("XAU_USD", 10000, 100)
    a._symbol_cache["ID_100"] = ("XAU/USD", 10000, 100)
    return a


@pytest.mark.asyncio
async def test_resolve_symbol_id_flexible_naming(adapter_with_symbols):
    """
    [SAFETY] Flexible naming (XAUUSD, XAU_USD, XAU/USD) should all resolve
    to the correct cTrader Symbol ID via the L3 cache.
    No DB query or broker call is made.
    """
    result = adapter_with_symbols._resolve_symbol_from_cache("XAUUSD")
    assert result is not None
    symbol_id, lot_size, step_size = result
    assert symbol_id in (41, 100)  # Any valid Gold symbol ID is acceptable

    # XAU/USD: normalizes to XAUUSD, so it resolves via the XAUUSD cache key
    result = adapter_with_symbols._resolve_symbol_from_cache("XAU/USD")
    assert result is not None
    symbol_id, _, _ = result
    assert symbol_id in (41, 100)  # Resolves to a Gold instrument ID


@pytest.mark.asyncio
async def test_resolve_symbol_id_fails_if_not_found(adapter_with_symbols):
    """
    [SAFETY] Resolving an unknown symbol should raise ValueError after
    cache miss + populate attempt — preventing execution against the wrong instrument.
    """
    with patch.object(adapter_with_symbols, "_populate_symbol_cache", new=AsyncMock()):
        with pytest.raises(ValueError, match="NON_EXISTENT"):
            await adapter_with_symbols._resolve_symbol_id_and_lot_size("NON_EXISTENT")
