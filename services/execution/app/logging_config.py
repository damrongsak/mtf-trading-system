import logging
import sys
from pythonjsonlogger import jsonlogger

from app.utils.tracing import request_id_ctx, get_request_id

class TracingFilter(logging.Filter):
    """
    Injects request_id from contextvars into the log record.
    """
    def filter(self, record):
        record.request_id = get_request_id()
        return True

def setup_logging(level=logging.INFO):
    """
    Configures structured JSON logging for Execution Service.
    """
    logger = logging.getLogger()
    logger.setLevel(level)

    # Console Handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Custom format with common fields and request_id
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s',
        rename_fields={"asctime": "timestamp", "levelname": "severity"},
        datefmt='%Y-%m-%dT%H:%M:%SZ'
    )
    
    handler.setFormatter(formatter)
    
    # Add Filter for request_id
    if not any(isinstance(f, TracingFilter) for f in logger.filters):
        logger.addFilter(TracingFilter())
    
    # Avoid duplicate handlers
    if not logger.handlers:
        logger.addHandler(handler)
        
    return logger

def set_correlation_id(cid: str):
    """Helper to set correlation ID for the current async task (Legacy name preserved for compat)."""
    return request_id_ctx.set(cid)

def reset_correlation_id(token):
    """Helper to reset correlation ID context (Legacy name preserved for compat)."""
    request_id_ctx.reset(token)
