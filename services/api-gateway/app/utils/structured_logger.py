"""
G4: Structured Logger with trace_id support.

Every WS command produces a JSON log line for post-trade audit:
  {"ts": 1234567890.1, "trace_id": "...", "cmd": "execute", "api_key": "...", "status": "success", "latency_ms": 18}

Usage:
    from app.utils.structured_logger import structured_log

    start = time.monotonic()
    result = await _handle_command(...)
    structured_log(trace_id, cmd, api_key, result.get("status"), start)
"""
import json
import logging
import time
from typing import Optional

# Dedicated audit logger for trade commands — separate from application logs
_audit_logger = logging.getLogger("audit.ws_command")

# Ensure JSON format for easy ingestion by log aggregators (e.g., CloudWatch, Datadog)
class _JsonFormatter(logging.Formatter):
    """Emit log records as single JSON lines."""
    def format(self, record: logging.LogRecord) -> str:
        payload = record.msg if isinstance(record.msg, dict) else {"message": record.msg}
        payload["level"] = record.levelname
        return json.dumps(payload, default=str)


def _setup_audit_logger() -> None:
    if not _audit_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_JsonFormatter())
        _audit_logger.addHandler(handler)
        _audit_logger.setLevel(logging.INFO)
        _audit_logger.propagate = False  # Don't bubble up to root logger


_setup_audit_logger()


def structured_log(
    trace_id: str,
    cmd: str,
    api_key: str,
    status: str,
    start_monotonic: float,
    extra: Optional[dict] = None,
) -> None:
    """
    Emit a structured JSON audit log line for a WebSocket command.

    Args:
        trace_id:        Client-supplied command ID (doubles as trace ID)
        cmd:             Command name (e.g., 'execute', 'close')
        api_key:         First 8 chars of the API key for correlation (never log full key)
        status:          Outcome: 'success', 'error', 'duplicate', 'service_unavailable'
        start_monotonic: time.monotonic() captured before command execution
        extra:           Optional additional fields (e.g., order_id, instrument)
    """
    latency_ms = round((time.monotonic() - start_monotonic) * 1000, 2)
    record = {
        "ts": time.time(),
        "trace_id": trace_id,
        "cmd": cmd,
        "api_key": api_key[:8] + "..." if len(api_key) > 8 else api_key,
        "status": status,
        "latency_ms": latency_ms,
    }
    if extra:
        record.update(extra)
    _audit_logger.info(record)
