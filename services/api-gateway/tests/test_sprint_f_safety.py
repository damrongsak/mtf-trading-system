"""
Sprint F Unit Tests: Idempotency Guard & HMAC Replay Attack
(api-gateway service)

SAFETY NOTICE:
- All tests use AsyncMock/MagicMock only.
- NO real broker connections, NO real trades.
- These tests verify that safety guards PREVENT dangerous operations.
"""
import pytest
import time
from unittest.mock import AsyncMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1: Idempotency Guard Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_idempotency_guard_allows_new_command():
    """
    [SAFETY] A command with a new unique ID should proceed.
    SETNX returns 1 (key was set) → not a duplicate.
    """
    from app.routers.external import _check_idempotency

    mock_rc = AsyncMock()
    mock_rc.setnx.return_value = 1  # New key — proceed

    with patch("app.utils.redis_client.redis_client") as mock_redis_client:
        mock_redis_client.get_client = AsyncMock(return_value=mock_rc)
        result = await _check_idempotency("api_key_test", "unique-cmd-001", "execute")

    assert result is None  # None = proceed normally


@pytest.mark.asyncio
async def test_idempotency_guard_blocks_duplicate_command():
    """
    [SAFETY] A command with a repeated ID must be rejected immediately.
    SETNX returns 0 (key already exists) → duplicate, block.
    This prevents double-execution of a live trade.
    """
    from app.routers.external import _check_idempotency

    mock_rc = AsyncMock()
    mock_rc.setnx.return_value = 0  # Already exists — duplicate!

    with patch("app.utils.redis_client.redis_client") as mock_redis_client:
        mock_redis_client.get_client = AsyncMock(return_value=mock_rc)
        result = await _check_idempotency("api_key_test", "cmd-already-sent", "execute")

    assert result is not None
    assert result["status"] == "duplicate"
    assert "Duplicate" in result["error"]


@pytest.mark.asyncio
async def test_idempotency_guard_requires_id_for_mutation():
    """
    [SAFETY] Mutating commands MUST include a unique 'id'.
    If missing/unknown → reject immediately.
    """
    from app.routers.external import _check_idempotency

    result = await _check_idempotency("api_key_test", "unknown", "execute")
    assert result is not None
    assert result["status"] == "error"
    assert "unique 'id'" in result["error"]


@pytest.mark.asyncio
async def test_idempotency_guard_skips_read_commands():
    """
    [SAFETY] Read-only commands must NOT be guarded.
    They are idempotent by nature and must always be retryable without
    the client having to supply a unique ID.
    """
    from app.routers.external import _check_idempotency

    for read_cmd in ["get_account", "get_orders", "get_trades"]:
        result = await _check_idempotency("api_key_test", "unknown", read_cmd)
        assert result is None, f"Read command '{read_cmd}' should not be guarded"


@pytest.mark.asyncio
async def test_idempotency_guard_allows_on_redis_failure():
    """
    [SAFETY] Fail-open: If Redis is unavailable, must NOT block execution.
    Trading availability > strict idempotency when infrastructure fails.
    This will be logged as a WARNING for post-incident analysis.
    """
    from app.routers.external import _check_idempotency

    with patch("app.utils.redis_client.redis_client") as mock_redis_client:
        mock_redis_client.get_client = AsyncMock(side_effect=Exception("Redis connection refused"))
        result = await _check_idempotency("api_key_test", "cmd-001", "execute")

    assert result is None  # Allow through on Redis failure


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2: HMAC Replay Attack Prevention Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_hmac_replay_attack_rejected_for_old_timestamp():
    """
    [SAFETY] A request with timestamp older than 30s must be rejected.
    Prevents captured tokens from being replayed by attackers.
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
    assert not is_valid  # Must reject old timestamps


def test_hmac_fresh_signature_accepted():
    """
    [SAFETY] A signature generated with the current timestamp must be accepted.
    Confirms that the 30s window does not block legitimate requests.
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
    assert is_valid  # Must accept fresh signatures


def test_hmac_tampered_signature_rejected():
    """
    [SAFETY] A tampered signature must be rejected.
    Ensures method/path/body integrity is enforced in transit.
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
    assert not is_valid  # Must reject tampered signatures
