import uuid
import asyncio
from functools import wraps
from contextlib import contextmanager, asynccontextmanager
from app.utils.tracing import request_id_ctx

def with_tracing(func):
    """
    Decorator to inject a unique correlation ID into a background job's context.
    Prefixes the ID with 'job-' and the function name for easy identification.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        job_name = func.__name__
        correlation_id = f"job-{job_name}-{uuid.uuid4().hex[:8]}"
        
        # Set the context variable
        token = request_id_ctx.set(correlation_id)
        try:
            return await func(*args, **kwargs)
        finally:
            # Reset context after execution
            request_id_ctx.reset(token)
            
    return wrapper

@asynccontextmanager
async def tracing_context(name: str):
    """
    Async context manager for tracing blocks of code in long-running loops.
    """
    correlation_id = f"{name}-{uuid.uuid4().hex[:8]}"
    token = request_id_ctx.set(correlation_id)
    try:
        yield correlation_id
    finally:
        request_id_ctx.reset(token)
