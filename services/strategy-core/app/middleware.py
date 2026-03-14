import uuid
import contextvars
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.utils.tracing import request_id_ctx, get_request_id

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Support both headers for inbound propagation
        correlation_id = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(correlation_id)
        try:
            response: Response = await call_next(request)
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Request-ID"] = correlation_id
            return response
        finally:
            request_id_ctx.reset(token)
