import contextvars

# Global tracing context
request_id_ctx = contextvars.ContextVar("request_id", default=None)
account_id_ctx = contextvars.ContextVar("account_id", default=None)
user_id_ctx = contextvars.ContextVar("user_id", default=None)
fund_id_ctx = contextvars.ContextVar("fund_id", default=None)

def get_request_id() -> str:
    """Helper to get the current request/correlation ID from context."""
    return request_id_ctx.get() or ""

def get_account_id() -> str:
    """Helper to get the current broker account ID from context."""
    return account_id_ctx.get() or ""

def get_user_id() -> str:
    """Helper to get the current User ID from context."""
    return user_id_ctx.get() or ""

def get_fund_id() -> str:
    """Helper to get the current Fund ID from context."""
    return fund_id_ctx.get() or ""
