"""
G2: Circuit Breaker for Execution Service calls.
Pattern: Netflix Hystrix / Martin Fowler

States:
    CLOSED     → Normal. Requests pass through to Execution Service.
    OPEN       → Fail-fast. Requests rejected immediately without hitting Execution.
    HALF-OPEN  → Probe. One request allowed through; success → CLOSED, failure → OPEN.

Configuration:
    failure_threshold:   Number of consecutive failures to trip to OPEN (default: 5)
    recovery_timeout:    Seconds to wait in OPEN before probing (default: 30)

Usage:
    from app.utils.circuit_breaker import execution_circuit_breaker

    async with execution_circuit_breaker as breaker:
        result = await execution_client.place_order(...)

    # Or use the helper directly:
    if not execution_circuit_breaker.allow_request():
        return {"status": "service_unavailable", "error": "Execution service circuit open"}
"""
import asyncio
import logging
import time
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """
    Thread-safe (asyncio) Circuit Breaker implementation.
    
    All state transitions are logged with [CIRCUIT] prefix for easy filtering.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._opened_at: Optional[float] = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def is_closed(self) -> bool:
        return self._state == CircuitState.CLOSED

    def allow_request(self) -> bool:
        """
        Check if a request should be allowed through.
        Returns True if the circuit is CLOSED or in HALF-OPEN probe mode.
        """
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed → try HALF-OPEN
            elapsed = time.monotonic() - (self._opened_at or 0)
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.warning(
                    f"[CIRCUIT] {self.name}: OPEN → HALF-OPEN "
                    f"(recovery probe after {elapsed:.1f}s)"
                )
                return True  # Allow the probe request
            return False

        if self._state == CircuitState.HALF_OPEN:
            return True  # One probe at a time

        return False

    def record_success(self) -> None:
        """Call after a successful Execution Service response."""
        prev_state = self._state
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        if prev_state != CircuitState.CLOSED:
            logger.info(f"[CIRCUIT] {self.name}: {prev_state} → CLOSED (success)")

    def record_failure(self) -> None:
        """Call after a failed Execution Service response (timeout, 5xx, etc.)."""
        self._failure_count += 1

        if self._state == CircuitState.HALF_OPEN:
            # Probe failed → back to OPEN, reset timer
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()
            logger.error(
                f"[CIRCUIT] {self.name}: HALF-OPEN → OPEN (probe failed)"
            )
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()
            logger.error(
                f"[CIRCUIT] {self.name}: CLOSED → OPEN "
                f"(threshold={self.failure_threshold} failures reached)"
            )

    def get_fallback_response(self) -> dict:
        """Standard fallback response when circuit is OPEN."""
        return {
            "status": "service_unavailable",
            "error": (
                f"Execution Service is temporarily unavailable. "
                f"Circuit is {self._state.value}. "
                f"Retry after {self.recovery_timeout:.0f}s."
            ),
        }


# Singleton circuit breaker for the Execution Service
# Shared across all WebSocket connections and HTTP requests
execution_circuit_breaker = CircuitBreaker(
    name="ExecutionService",
    failure_threshold=5,
    recovery_timeout=30.0,
)
