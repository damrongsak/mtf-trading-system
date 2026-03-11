import logging
import sys
import contextvars
from pythonjsonlogger import jsonlogger

# ContextVar for correlation_id (to be set by workers)
correlation_id_ctx = contextvars.ContextVar("correlation_id", default=None)

class WorkerContextFilter(logging.Filter):
    """
    Injects correlation_id from contextvars into the log record.
    """
    def filter(self, record):
        correlation_id = correlation_id_ctx.get()
        record.correlation_id = correlation_id or ""
        return True

def setup_logging(level=logging.INFO):
    """
    Configures structured JSON logging for Execution Service.
    """
    logger = logging.getLogger()
    logger.setLevel(level)

    # Console Handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Custom format with common fields and correlation_id
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(correlation_id)s %(message)s',
        rename_fields={"asctime": "timestamp", "levelname": "severity"},
        datefmt='%Y-%m-%dT%H:%M:%SZ'
    )
    
    handler.setFormatter(formatter)
    
    # Add Filter for correlation_id
    if not any(isinstance(f, WorkerContextFilter) for f in logger.filters):
        logger.addFilter(WorkerContextFilter())
    
    # Avoid duplicate handlers
    if not logger.handlers:
        logger.addHandler(handler)
        
    return logger

def set_correlation_id(cid: str):
    """Helper to set correlation ID for the current async task."""
    return correlation_id_ctx.set(cid)

def reset_correlation_id(token):
    """Helper to reset correlation ID context."""
    correlation_id_ctx.reset(token)
