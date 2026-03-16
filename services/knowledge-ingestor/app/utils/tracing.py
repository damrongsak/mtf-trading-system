import contextvars

# Global tracing context
request_id_ctx = contextvars.ContextVar("request_id", default=None)

def get_request_id() -> str:
    """Helper to get the current request/correlation ID from context."""
    return request_id_ctx.get() or ""
