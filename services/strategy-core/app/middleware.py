import uuid
import contextvars
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# ContextVar to store correlation/request ID across the request life-cycle
correlation_id_ctx = contextvars.ContextVar("correlation_id", default=None)

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = correlation_id_ctx.set(correlation_id)
        try:
            response: Response = await call_next(request)
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            correlation_id_ctx.reset(token)

def get_correlation_id() -> str:
    return correlation_id_ctx.get()
