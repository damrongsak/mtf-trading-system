import uuid
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.tracing import request_id_ctx
from app.core.logger import get_logger

logger = get_logger("Middleware")

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Extract or Generate Request ID
        request_id = request.headers.get("X-Request-ID") or \
                     request.headers.get("X-Correlation-ID") or \
                     str(uuid.uuid4())
        
        # 2. Set in Context
        token = request_id_ctx.set(request_id)
        
        start_time = time.time()
        try:
            # 3. Process Request
            response = await call_next(request)
            
            # 4. Attach to Response Headers
            response.headers["X-Request-ID"] = request_id
            
            process_time = (time.time() - start_time) * 1000
            logger.info(
                "request_processed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "latency_ms": round(process_time, 2)
                }
            )
            return response
        finally:
            # 5. Reset Context
            request_id_ctx.reset(token)
