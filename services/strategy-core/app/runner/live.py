import asyncio
import logging
from app.engine import StrategyEngine
from app.streaming.subscriber import RedisSubscriber

logger = logging.getLogger(__name__)

class LiveRunner:
    def __init__(self, engine: StrategyEngine):
        self.engine = engine
        # Use the robust subscriber with a callback
        self.subscriber = RedisSubscriber(self._on_tick)
        self._running = False

    async def _on_tick(self, channel: str, data: dict):
        """Callback for received tick data."""
        try:
             await self.engine.on_tick(data)
        except Exception as e:
            logger.error(f"Error processing tick in engine: {e}")

    async def start(self):
        if self._running:
            return
        
        self._running = True
        logger.info("LiveRunner starting...")
        try:
            # Subscribe to all market data using the pattern
            await self.subscriber.psubscribe(["market_data:*"])
        except Exception as e:
            logger.error(f"Failed to start LiveRunner: {e}")
            self._running = False

    async def stop(self):
        self._running = False
        await self.subscriber.stop()
        logger.info("LiveRunner stopped")

# Global instance
from app.engine import strategy_engine # We need to ensure singleton pattern
live_runner = LiveRunner(strategy_engine)
