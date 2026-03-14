import uuid
import contextvars
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.utils.tracing import request_id_ctx, get_request_id
logger = logging.getLogger(__name__)

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        try:
            # Log incoming request here where we have the context
            logger.info(f"Incoming: {request.method} {request.url.path}")
            
            request.state.request_id = request_id
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_ctx.reset(token)
