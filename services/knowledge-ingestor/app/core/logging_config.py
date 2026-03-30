import logging
import sys
from pythonjsonlogger import jsonlogger
from app.utils.tracing import get_request_id

class TracingFilter(logging.Filter):
    """
    Injects request_id from contextvars into the log record.
    """
    def filter(self, record):
        record.request_id = get_request_id()
        return True

class HumanFormatter(logging.Formatter):
    """Custom formatter for clear professional console output in development."""
    def format(self, record):
        prefix = ""
        if record.levelno >= logging.ERROR:
            prefix = "❌ "
        elif record.levelno >= logging.WARNING:
            prefix = "⚠️ "
        elif record.levelno >= logging.INFO:
            prefix = "✨ "

        rid = getattr(record, "request_id", None)
        rid_str = f"| {rid[:8]} " if rid else ""
        msg = super().format(record)
        return f"{prefix}{rid_str}| {record.name} | {msg}"

def setup_logging(level=logging.INFO):
    """
    Configures standardized logging for Knowledge Ingestor.
    """
    logger = logging.getLogger()
    logger.setLevel(level)

    # 1. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Standard JSON Formatter
    json_formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "severity"},
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    
    # Conditional Formatter based on config
    from app.core.app_config import config
    is_json = getattr(config, "ki_log_format", "human") == "json"
    
    if is_json:
        console_handler.setFormatter(json_formatter)
    else:
        console_handler.setFormatter(HumanFormatter("%(message)s"))

    # Add Tracing Filter
    if not any(isinstance(f, TracingFilter) for f in logger.filters):
        logger.addFilter(TracingFilter())

    # Add Console Handler
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        logger.addHandler(console_handler)

    # 2. Persistent JSON Error Log File Handler (Standardized)
    try:
        from pathlib import Path
        log_dir = Path("/app/logs")
        log_dir.mkdir(exist_ok=True, parents=True)
        error_log_path = log_dir / "ingestion_errors.json"

        file_handler = logging.FileHandler(str(error_log_path))
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(json_formatter)

        if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
            logger.addHandler(file_handler)
    except Exception:
        # Silently fail if file logging cannot be initialized (e.g. read-only fs)
        pass

    return logger

def get_logger(name: str):
    """Get a logger instance."""
    return logging.getLogger(name)

# Initialize on import to maintain singleton behavior
setup_logging()
