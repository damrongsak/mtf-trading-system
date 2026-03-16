import sys
import logging
import structlog
from app.utils.tracing import get_request_id

def add_request_id(logger, method_name, event_dict):
    """Processor to inject request_id from contextvars."""
    event_dict["request_id"] = get_request_id()
    return event_dict

def setup_logging():
    """Configure professional structured logging for Project Olympus (Production Optimized)."""
    
    # Standard library bridge logic
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.contextvars.merge_contextvars,
        add_request_id,  # Inject request_id
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
    ]

    # Use JSON in production (non-TTY) or if forced via env
    if not sys.stderr.isatty():
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Bridge standard logging to structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=logging.INFO,
    )

def get_logger(name: str):
    """Get a structured logger instance."""
    return structlog.get_logger(name)

# Initialize on import
setup_logging()
