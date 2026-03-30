import logging
import sys
from pythonjsonlogger import jsonlogger
from app.utils.tracing import get_request_id


def setup_logging(level=logging.INFO):
    """
    Configures standardized logging for Knowledge Ingestor.
    Console: Human-readable by default.
    File: JSON for production audits.
    """
    logger = logging.getLogger()
    logger.setLevel(level)

    # 1. Human-Readable Console Handler (for dev/logs visibility)
    console_handler = logging.StreamHandler(sys.stdout)

    class HumanFormatter(logging.Formatter):
        """Custom formatter for clear professional console output."""

        def format(self, record):
            # Styling markers
            prefix = ""
            if record.levelno >= logging.ERROR:
                prefix = "❌ "
            elif record.levelno >= logging.WARNING:
                prefix = "⚠️ "
            elif record.levelno >= logging.INFO:
                prefix = "✨ "

            # Extract request_id if exists
            rid = getattr(record, "request_id", None)
            rid_str = f"| {rid[:8]} " if rid else ""

            # Clean message
            msg = super().format(record)
            return f"{prefix}{rid_str}| {record.name} | {msg}"

    console_formatter = HumanFormatter("%(message)s")
    json_formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "severity"},
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )

    # Choose console format based on config (fallback to human if local/dev)
    from app.core.app_config import config

    is_json = getattr(config, "ki_log_format", "human") == "json"
    console_handler.setFormatter(json_formatter if is_json else console_formatter)

    # Custom tracing filter
    class TracingFilter(logging.Filter):
        def filter(self, record):
            record.request_id = get_request_id()
            return True

    if not any(isinstance(f, TracingFilter) for f in logger.filters):
        logger.addFilter(TracingFilter())

    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        logger.addHandler(console_handler)

    # 2. Persistent JSON Error Log File Handler
    try:
        from pathlib import Path

        log_dir = Path("/app/logs")
        log_dir.mkdir(exist_ok=True, parents=True)
        error_log_path = (
            log_dir / "ingestion_errors.json"
        )  # RENAMED to .json for clarity

        file_handler = logging.FileHandler(str(error_log_path))
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(json_formatter)

        if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
            logger.addHandler(file_handler)
            logger.info(f"📁 Persistent JSON audits initialized at: {error_log_path}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize file logging: {e}")

    return logger


def get_logger(name: str):
    """Get a logger instance."""
    return logging.getLogger(name)


# Initialize on import
setup_logging()
