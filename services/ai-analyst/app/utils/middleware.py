import uuid
import contextvars
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.utils.tracing import request_id_ctx, get_request_id

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

import logging

from pythonjsonlogger import jsonlogger

def setup_tracing_logging():
    """Configures the ROOT logger to use JSON structured logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler()
    
    # Custom filter to inject request_id
    class TracingFilter(logging.Filter):
        def filter(self, record):
            # Ensure request_id is never None for JSON serialization
            record.request_id = get_request_id() or ""
            return True
            
    if not any(isinstance(f, TracingFilter) for f in root_logger.filters):
        root_logger.addFilter(TracingFilter())

    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s',
        rename_fields={"asctime": "timestamp", "levelname": "severity"},
        datefmt='%Y-%m-%dT%H:%M:%SZ'
    )
    handler.setFormatter(formatter)
    
    # Remove existing handlers to avoid duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()
        
    root_logger.addHandler(handler)
    return root_logger
