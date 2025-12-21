import asyncio
import logging
import json
from app.engine import StrategyEngine
from app.utils.redis_subscriber import RedisSubscriber

logger = logging.getLogger(__name__)

class LiveRunner:
    def __init__(self, engine: StrategyEngine):
        self.engine = engine
        self.subscriber = RedisSubscriber()
        self._running = False
        self._task = None

    async def start(self):
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("LiveRunner started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.subscriber.close()
        logger.info("LiveRunner stopped")

    async def _run_loop(self):
        # Determine unique symbols from active strategies
        # For now, we assume strategies might be added dynamically.
        
        # In Redis arch, data is pushed to channels like market_data:EUR_USD
        # We should subscribe to *all* market data or specific ones. 
        # For broad coverage in this MVP, let's look for pattern market_data:*
        
        try:
            await self.subscriber.connect()
            # Redis psubscribe for pattern matching
            await self.subscriber.pubsub.psubscribe("market_data:*")
            
            async for msg in self.subscriber.listen():
                if msg["type"] == "pmessage": # Pattern message
                    data_str = msg["data"]
                    try:
                         # Redis sends string, parse to JSON
                         data = json.loads(data_str)
                         # Forward to engine
                         await self.engine.on_tick(data)
                    except json.JSONDecodeError:
                        logger.error("Failed to decode market data JSON")
                
        except asyncio.CancelledError:
            logger.info("LiveRunner loop cancelled")
        except Exception as e:
            logger.error(f"LiveRunner error: {e}")
            # Optional: retry logic using simple sleep for MVP
            await asyncio.sleep(5)

# Global instance
from app.engine import strategy_engine # We need to ensure singleton pattern
live_runner = LiveRunner(strategy_engine)
