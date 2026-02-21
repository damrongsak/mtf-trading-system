import logging
import sys
from src.app.core.config import settings

def setup_logging():
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    # Reduce noise from broad libraries
    logging.getLogger("yfinance").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.INFO)
