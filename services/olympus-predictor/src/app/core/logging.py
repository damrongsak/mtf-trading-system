import logging
import sys
from pythonjsonlogger import jsonlogger
from src.app.core.config import settings
from src.app.utils.tracing import get_request_id

class TracingFilter(logging.Filter):
    """
    Injects request_id from contextvars into the log record.
    """
    def filter(self, record):
        record.request_id = get_request_id()
        return True

def setup_logging():
    """
    Configures structured JSON logging with request tracing.
    """
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))

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

    # Reduce noise from broad libraries
    logging.getLogger("yfinance").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.INFO)
    
    return logger
