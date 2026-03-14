import uuid
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.tracing import request_id_ctx

logger = logging.getLogger(__name__)

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Extract or Generate Request ID
        request_id = request.headers.get("X-Request-ID") or \
                     request.headers.get("X-Correlation-ID") or \
                     str(uuid.uuid4())
        
        # 2. Set in Context (accessible by all downstream async tasks)
        token = request_id_ctx.set(request_id)
        
        start_time = time.time()
        try:
            # 3. Process Request
            response = await call_next(request)
            
            # 4. Attach to Response Headers
            response.headers["X-Request-ID"] = request_id
            
            process_time = (time.time() - start_time) * 1000
            logger.info(
                f"Request: {request.method} {request.url.path} "
                f"Status: {response.status_code} "
                f"Latency: {process_time:.2f}ms"
            )
            return response
        finally:
            # 5. Reset Context to avoid bleeding into other requests (important!)
            request_id_ctx.reset(token)
