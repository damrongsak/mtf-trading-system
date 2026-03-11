---
name: logging-standard
description: Best practices and templates for implementing standardized JSON logging and correlation ID propagation across all microservices.
---

# Logging & Correlation Standard Skill

This skill provides the necessary instructions and code templates to implement structured JSON logging and request tracing (Correlation IDs) in the MTF Trading System, ensuring compliance with **Observability Guardrails**.

## Core Principles
1. **Always JSON**: Use `pythonjsonlogger.jsonlogger.JsonFormatter`.
2. **Always Trace**: Every log must include `request_id` or `correlation_id`.
3. **Always Singleton**: Use `app.utils.tracing` for `contextvars`.

## Implementation Workflow

### 1. Unified Tracing Context
Create or update `app/utils/tracing.py` to act as the single source for the request context.

```python
import contextvars
request_id_ctx = contextvars.ContextVar("request_id", default=None)
```

### 2. Standardized Logging Config
Implement `app/logging_config.py` using this template:

```python
import logging
import sys
from pythonjsonlogger import jsonlogger
from app.utils.tracing import request_id_ctx

def setup_logging(level=logging.INFO):
    logger = logging.getLogger()
    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    
    class TracingFilter(logging.Filter):
        def filter(self, record):
            # Injects the ID from ContextVar into every LogRecord
            record.request_id = request_id_ctx.get() or ""
            return True
            
    if not any(isinstance(f, TracingFilter) for f in logger.filters):
        logger.addFilter(TracingFilter())

    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s',
        rename_fields={"asctime": "timestamp", "levelname": "severity"},
        datefmt='%Y-%m-%dT%H:%M:%SZ'
    )
    handler.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(handler)
    return logger
```

### 3. Middleware Integration (FastAPI)
Standardize `app/middleware.py`:

```python
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.tracing import request_id_ctx

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_ctx.reset(token)
```

## Verification
- Run the service and check `docker compose logs`.
- Verify the output is valid JSON.
- Verify `request_id` is present in logs during an API request.
