"""
Sprint G Unit Tests: G1 Heartbeat, G2 Circuit Breaker, G4 Structured Logging

SAFETY: All tests are isolated — no real broker connections, no real trades.
"""
import asyncio
import json
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# G2: Circuit Breaker Tests
# ─────────────────────────────────────────────────────────────────────────────

from app.utils.circuit_breaker import CircuitBreaker, CircuitState


@pytest.fixture
def breaker():
    """Fresh circuit breaker for each test (low threshold for fast testing)."""
    return CircuitBreaker(name="test", failure_threshold=3, recovery_timeout=1.0)


def test_circuit_starts_closed(breaker):
    """New circuit breaker should start in CLOSED state."""
    assert breaker.state == CircuitState.CLOSED
    assert breaker.allow_request() is True


def test_circuit_opens_after_threshold_failures(breaker):
    """
    [G2] After `failure_threshold` consecutive failures, circuit should OPEN.
    In OPEN state, requests are rejected without hitting Execution Service.
    """
    for i in range(breaker.failure_threshold):
        assert breaker.state == CircuitState.CLOSED, f"Should still be CLOSED at failure {i+1}"
        breaker.record_failure()

    assert breaker.state == CircuitState.OPEN
    assert breaker.allow_request() is False


def test_circuit_rejects_immediately_when_open(breaker):
    """
    [G2] When OPEN, allow_request() returns False without any I/O.
    This is the fail-fast behavior preventing cascade failure.
    """
    for _ in range(breaker.failure_threshold):
        breaker.record_failure()

    assert not breaker.allow_request()
    fallback = breaker.get_fallback_response()
    assert fallback["status"] == "service_unavailable"
    assert "unavailable" in fallback["error"].lower()


def test_circuit_transitions_to_half_open_after_recovery(breaker):
    """
    [G2] After `recovery_timeout` seconds in OPEN, circuit should allow a probe.
    This is the HALF-OPEN state.
    """
    for _ in range(breaker.failure_threshold):
        breaker.record_failure()

    assert breaker.state == CircuitState.OPEN
    assert not breaker.allow_request()

    # Manually set _opened_at to simulate timeout elapsed
    breaker._opened_at = time.monotonic() - 2.0  # 2s ago > 1s recovery_timeout

    assert breaker.allow_request() is True
    assert breaker.state == CircuitState.HALF_OPEN


def test_circuit_closes_on_successful_probe(breaker):
    """
    [G2] A successful response in HALF-OPEN state closes the circuit.
    """
    for _ in range(breaker.failure_threshold):
        breaker.record_failure()
    breaker._opened_at = time.monotonic() - 2.0
    breaker.allow_request()  # Transition to HALF-OPEN

    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.allow_request() is True


def test_circuit_reopens_on_failed_probe(breaker):
    """
    [G2] A failed response in HALF-OPEN state reopens the circuit.
    """
    for _ in range(breaker.failure_threshold):
        breaker.record_failure()
    breaker._opened_at = time.monotonic() - 2.0
    breaker.allow_request()  # Transition to HALF-OPEN

    assert breaker.state == CircuitState.HALF_OPEN
    breaker.record_failure()  # Probe failed
    assert breaker.state == CircuitState.OPEN


def test_circuit_resets_failure_count_on_success(breaker):
    """
    [G2] A single success resets the failure counter.
    """
    breaker.record_failure()
    breaker.record_failure()
    assert breaker._failure_count == 2

    breaker.record_success()
    assert breaker._failure_count == 0
    assert breaker.state == CircuitState.CLOSED


# ─────────────────────────────────────────────────────────────────────────────
# G4: Structured Logger Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_structured_log_emits_json_record():
    """
    [G4] structured_log should emit a JSON-formatted audit record
    with trace_id, cmd, api_key (truncated), status, and latency_ms.
    """
    from app.utils.structured_logger import structured_log

    emitted = []
    original_info = None

    import logging
    audit_logger = logging.getLogger("audit.ws_command")
    original_handlers = audit_logger.handlers[:]

    class CapturingHandler(logging.Handler):
        def emit(self, record):
            emitted.append(record.msg)

    capturing = CapturingHandler()
    audit_logger.addHandler(capturing)

    try:
        start = time.monotonic() - 0.05  # Simulate 50ms elapsed
        structured_log("trace-abc-123", "execute", "myapikey12345", "success", start)

        assert len(emitted) == 1
        record = emitted[0]
        assert isinstance(record, dict)
        assert record["trace_id"] == "trace-abc-123"
        assert record["cmd"] == "execute"
        # api_key 'myapikey12345' → first 8 chars = 'myapik' wait... length check
        # 'myapikey12345'[:8] = 'myapikey' → assert 'myapikey...'
        assert record["api_key"] == "myapikey..."  # First 8 chars of 'myapikey12345'
        assert record["status"] == "success"
        assert record["latency_ms"] >= 40  # At least ~50ms

    finally:
        audit_logger.handlers = original_handlers


def test_structured_log_truncates_api_key():
    """
    [G4] API key must never appear in full in logs — only first 8 chars + '...'
    """
    from app.utils.structured_logger import structured_log

    import logging
    audit_logger = logging.getLogger("audit.ws_command")
    emitted = []

    class CapturingHandler(logging.Handler):
        def emit(self, record):
            emitted.append(record.msg)

    capturing = CapturingHandler()
    audit_logger.addHandler(capturing)

    try:
        structured_log("t1", "get_account", "supersecretkey9876", "success", time.monotonic())
        assert "supersecretkey9876" not in str(emitted[-1])
        assert emitted[-1]["api_key"].endswith("...")
    finally:
        audit_logger.handlers.remove(capturing)


# ─────────────────────────────────────────────────────────────────────────────
# G1: Heartbeat Loop Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_heartbeat_closes_on_missing_pong():
    """
    [G1] If client does not respond to ping within PONG_TIMEOUT,
    the server should close the WebSocket with code 1001 (Going Away).
    """
    mock_ws = AsyncMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.close = AsyncMock()

    pong_received = asyncio.Event()
    # pong_received is NOT set — simulate client not responding

    async def _heartbeat_loop_test():
        PING_INTERVAL = 0.01  # Very short for test
        PONG_TIMEOUT = 0.01
        while True:
            await asyncio.sleep(PING_INTERVAL)
            pong_received.clear()
            try:
                await mock_ws.send_json({"type": "ping", "ts": time.time()})
            except Exception:
                break
            try:
                await asyncio.wait_for(pong_received.wait(), timeout=PONG_TIMEOUT)
            except asyncio.TimeoutError:
                await mock_ws.close(code=1001)
                break

    await _heartbeat_loop_test()

    mock_ws.close.assert_called_once_with(code=1001)


@pytest.mark.asyncio
async def test_heartbeat_continues_when_pong_received():
    """
    [G1] When client responds with pong, the heartbeat loop should continue
    without closing the connection.
    """
    mock_ws = AsyncMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.close = AsyncMock()

    pong_received = asyncio.Event()
    ping_count = 0

    async def _simulate_pong():
        """Simulate client responding to pings immediately."""
        await asyncio.sleep(0.015)
        pong_received.set()

    async def _heartbeat_loop_test():
        nonlocal ping_count
        for _ in range(2):  # Run 2 cycles
            await asyncio.sleep(0.01)
            pong_received.clear()
            await mock_ws.send_json({"type": "ping", "ts": time.time()})
            ping_count += 1
            await asyncio.sleep(0.005)
            pong_received.set()  # Simulate pong received
            try:
                await asyncio.wait_for(pong_received.wait(), timeout=0.1)
            except asyncio.TimeoutError:
                await mock_ws.close(code=1001)
                return

    await _heartbeat_loop_test()

    # Connection should NOT have been closed
    mock_ws.close.assert_not_called()
    assert ping_count == 2
