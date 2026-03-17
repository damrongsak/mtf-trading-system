import logging
import sys
from pythonjsonlogger import jsonlogger
from app.utils.tracing import get_request_id

def setup_logging(level=logging.INFO):
    """
    Configures standardized JSON logging for Knowledge Ingestor.
    """
    logger = logging.getLogger()
    logger.setLevel(level)

    # Console Handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Custom filter to inject request_id
    class TracingFilter(logging.Filter):
        def filter(self, record):
            record.request_id = get_request_id()
            return True
            
    if not any(isinstance(f, TracingFilter) for f in logger.filters):
        logger.addFilter(TracingFilter())

    # Custom format with common fields and request_id
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s',
        rename_fields={"asctime": "timestamp", "levelname": "severity"},
        datefmt='%Y-%m-%dT%H:%M:%SZ'
    )
    
    handler.setFormatter(formatter)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        logger.addHandler(handler)
        
    return logger

def get_logger(name: str):
    """Get a logger instance."""
    return logging.getLogger(name)

# Initialize on import
setup_logging()
