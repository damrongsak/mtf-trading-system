import contextvars

# Global tracing context
request_id_ctx = contextvars.ContextVar("request_id", default=None)
account_id_ctx = contextvars.ContextVar("account_id", default=None)

def get_request_id() -> str:
    """Helper to get the current request/correlation ID from context."""
    return request_id_ctx.get() or ""

def get_account_id() -> str:
    """Helper to get the current broker account ID from context."""
    return account_id_ctx.get() or ""
