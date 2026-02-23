import uuid
import contextvars
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# ContextVar for request_id
request_id_ctx = contextvars.ContextVar("request_id", default=None)

class TracingFormatter(logging.Formatter):
    def format(self, record):
        request_id = request_id_ctx.get()
        record.request_id = f"[{request_id}] " if request_id else ""
        return super().format(record)

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        try:
            request.state.request_id = request_id
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_ctx.reset(token)

def get_request_id() -> str:
    return request_id_ctx.get()
