import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging(level=logging.INFO):
    """
    Configures structured JSON logging for Strategy Core Service.
    """
    logger = logging.getLogger()
    logger.setLevel(level)

    # Console Handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Custom filter to inject correlation_id
    from app.middleware import correlation_id_ctx
    class TracingFilter(logging.Filter):
        def filter(self, record):
            record.correlation_id = correlation_id_ctx.get() or ""
            return True
            
    if not any(isinstance(f, TracingFilter) for f in logger.filters):
        logger.addFilter(TracingFilter())

    # Custom format with common fields
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(correlation_id)s %(message)s',
        rename_fields={"asctime": "timestamp", "levelname": "severity"},
        datefmt='%Y-%m-%dT%H:%M:%SZ'
    )
    
    handler.setFormatter(formatter)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        logger.addHandler(handler)
        
    return logger
