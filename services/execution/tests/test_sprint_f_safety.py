"""
Sprint F Unit Tests: Critical Safety Guards

SAFETY NOTICE:
- All tests use AsyncMock/MagicMock only.
- NO real broker connections, NO real trades.
- These tests verify that the safety guards PREVENT dangerous operations.
"""
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch, ANY

from app.adapters.ctrader import CTraderOrderAdapter, RiskValidationError


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def adapter():
    """Adapter with patched client and pre-populated L3 cache."""
    a = CTraderOrderAdapter("id", "secret", "12345", "token")
    a.client = AsyncMock()
    a._symbol_cache["XAU_USD"] = (93, 10000)
    a._symbol_cache["ID_93"] = ("XAU_USD", 10000)
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


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1: Idempotency Guard Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_idempotency_guard_allows_new_command():
    """
    [SAFETY] Idempotency: A command with a new unique ID should proceed.
    SETNX returns 1 (key was set) → not a duplicate.
    """
    from app.routers.external import _check_idempotency

    mock_rc = AsyncMock()
    mock_rc.setnx.return_value = 1  # New key — not a duplicate

    with patch("app.utils.redis_client.redis_client") as mock_redis_client:
        mock_redis_client.get_client = AsyncMock(return_value=mock_rc)
        result = await _check_idempotency("api_key_test", "unique-cmd-001", "execute")

    assert result is None  # None = proceed normally


@pytest.mark.asyncio
async def test_idempotency_guard_blocks_duplicate_command():
    """
    [SAFETY] Idempotency: A command with a repeated ID must be rejected.
    SETNX returns 0 (key already exists) → duplicate, block immediately.
    This prevents double-execution of a live trade.
    """
    from app.routers.external import _check_idempotency

    mock_rc = AsyncMock()
    mock_rc.setnx.return_value = 0  # Key already exists — duplicate!

    with patch("app.utils.redis_client.redis_client") as mock_redis_client:
        mock_redis_client.get_client = AsyncMock(return_value=mock_rc)
        result = await _check_idempotency("api_key_test", "cmd-already-sent", "execute")

    assert result is not None
    assert result["status"] == "duplicate"
    assert "Duplicate" in result["error"]


@pytest.mark.asyncio
async def test_idempotency_guard_requires_id_for_mutation():
    """
    [SAFETY] Mutating commands (execute, amend, close, cancel) MUST include
    a unique 'id'. If missing, reject immediately to enforce the safety policy.
    """
    from app.routers.external import _check_idempotency

    result = await _check_idempotency("api_key_test", "unknown", "execute")

    assert result is not None
    assert result["status"] == "error"
    assert "unique 'id'" in result["error"]


@pytest.mark.asyncio
async def test_idempotency_guard_skips_read_commands():
    """
    [SAFETY] Read-only commands (get_account, get_orders, get_trades) must NOT
    be guarded — they are idempotent by nature and must always be retryable.
    """
    from app.routers.external import _check_idempotency

    for read_cmd in ["get_account", "get_orders", "get_trades"]:
        result = await _check_idempotency("api_key_test", "unknown", read_cmd)
        assert result is None, f"Read command '{read_cmd}' should not be guarded"


@pytest.mark.asyncio
async def test_idempotency_guard_allows_on_redis_failure():
    """
    [SAFETY] Fail-open: If Redis is unavailable, the guard must NOT block
    execution. Availability > Safety in this case — the alternatives would be
    to stop all trading when Redis goes down.
    """
    from app.routers.external import _check_idempotency

    with patch("app.utils.redis_client.redis_client") as mock_redis_client:
        mock_redis_client.get_client = AsyncMock(side_effect=Exception("Redis connection refused"))
        result = await _check_idempotency("api_key_test", "cmd-001", "execute")

    assert result is None  # Allow through — don't block on infra failure


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2: HMAC Replay Attack Prevention Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_hmac_replay_attack_rejected_for_old_timestamp():
    """
    [SAFETY] HMAC: A request with a timestamp older than 30 seconds must be
    rejected. This prevents captured tokens from being replayed later.
    """
    from app.utils.hmac_utils import hmac_signer

    old_ts = str(time.time() - 60)  # 60 seconds ago — outside the 30s window
    is_valid = hmac_signer.verify_signature(
        secret="test_secret",
        signature="doesnt_matter",
        timestamp=old_ts,
        method="GET",
        path="/ws/command",
        body=""
    )
    assert not is_valid  # Must REJECT old timestamps


def test_hmac_fresh_signature_accepted():
    """
    [SAFETY] HMAC: A signature generated with the current timestamp must be
    accepted, confirming the 30s window allows normal operation.
    """
    from app.utils.hmac_utils import hmac_signer

    secret = "test_secret_456"
    ts = str(time.time())
    sig = hmac_signer.generate_signature(secret, ts, "GET", "/ws/command")

    is_valid = hmac_signer.verify_signature(
        secret=secret, signature=sig,
        timestamp=ts, method="GET",
        path="/ws/command", body=""
    )
    assert is_valid  # Must ACCEPT fresh signatures


def test_hmac_tampered_signature_rejected():
    """
    [SAFETY] HMAC: A signature that doesn't match the payload must be rejected.
    This ensures the method/path/body has not been tampered with in transit.
    """
    from app.utils.hmac_utils import hmac_signer

    secret = "test_secret_456"
    ts = str(time.time())
    real_sig = hmac_signer.generate_signature(secret, ts, "GET", "/ws/command")
    tampered_sig = real_sig[:-4] + "beef"  # tamper last 4 chars

    is_valid = hmac_signer.verify_signature(
        secret=secret, signature=tampered_sig,
        timestamp=ts, method="GET",
        path="/ws/command", body=""
    )
    assert not is_valid  # Must REJECT tampered signatures
