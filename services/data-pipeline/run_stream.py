import asyncio
import logging
import os
import sys

# Ensure we can import app
sys.path.append(os.getcwd())

from app.streaming.tick_streamer import TickStreamer
from app.database import SessionLocal
from app.repositories.market_repository import MarketRepository

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("stream_runner")

def fetch_supported_symbols():
    """
    Fetch active symbols from MarketRepository for OANDA.
    """
    db = SessionLocal()
    try:
        repo = MarketRepository(db)
        symbols = repo.get_active_symbols("OANDA")
        instrument_list = [s.symbol for s in symbols]
        logger.info(f"Loaded {len(instrument_list)} active symbols from DB: {instrument_list}")
        return instrument_list
    except Exception as e:
        logger.error(f"Failed to load symbols from DB: {e}")
        # Fallback to env or default
        symbols_env = os.getenv("STREAM_SYMBOLS", "EUR_USD,USD_JPY,XAU_USD")
        return [s.strip() for s in symbols_env.split(",") if s.strip()]
    finally:
        db.close()

async def main():
    instruments = fetch_supported_symbols()
    
    if not instruments:
        logger.error("No instruments found to stream. Exiting.")
        return
    
    logger.info(f"Initializing streamer for: {instruments}")
    
    streamer = TickStreamer()
    try:
        await streamer.run(instruments)
    except KeyboardInterrupt:
        logger.info("Stopping stream runner...")
    except Exception as e:
        logger.critical(f"Runner failed: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
