import logging
import sys

def setup_logging(level=logging.INFO):
    """
    Configures standard logging for API Gateway.
    """
    logger = logging.getLogger()
    logger.setLevel(level)

    # Console Handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Standard format with request_id
    from app.middleware import TracingFormatter
    formatter = TracingFormatter(
        '%(asctime)s [%(levelname)s] %(request_id)s%(name)s: %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%SZ'
    )
    
    handler.setFormatter(formatter)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        logger.addHandler(handler)
        
    return logger
