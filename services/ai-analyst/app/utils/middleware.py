import uuid
import contextvars
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# ContextVar to store request_id across the request life-cycle
request_id_ctx = contextvars.ContextVar("request_id", default=None)

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Get request ID from header or generate a new one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # 2. Set the context variable
        token = request_id_ctx.set(request_id)
        
        try:
            # 3. Attach it to the request state
            request.state.request_id = request_id
            
            # 4. Process the request
            response: Response = await call_next(request)
            
            # 5. Attach it to the response header
            response.headers["X-Request-ID"] = request_id
            
            return response
        finally:
            # 6. Reset the context variable
            request_id_ctx.reset(token)

def get_request_id() -> str:
    """Helper to get the current request ID from context."""
    return request_id_ctx.get()

import logging

class TracingFormatter(logging.Formatter):
    """Custom formatter that injects request_id into logs."""
    def format(self, record):
        request_id = get_request_id()
        record.request_id = f"[{request_id}] " if request_id else ""
        return super().format(record)

def setup_tracing_logging():
    """Configures the ROOT logger to use TracingFormatter."""
    # Use the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler()
    formatter = TracingFormatter(
        '%(asctime)s %(levelname)s %(request_id)s%(name)s: %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%SZ'
    )
    handler.setFormatter(formatter)
    
    # Remove existing handlers to avoid duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()
        
    root_logger.addHandler(handler)
    return root_logger
