import asyncio
import logging
from app.streaming import price_streamer
from app.engine import StrategyEngine

logger = logging.getLogger(__name__)

class LiveRunner:
    def __init__(self, engine: StrategyEngine, streamer: 'PriceStreamer'):
        self.engine = engine
        self.streamer = streamer
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
        logger.info("LiveRunner stopped")

    async def _run_loop(self):
        # Determine unique symbols from active strategies
        # For now, we assume strategies might be added dynamically, 
        # but let's start with a default set or query engine.
        # In this MVP, we might hardcode or query engine for active strategies.
        
        # We need to start the stream for ALL symbols used by active strategies
        active_symbols = ["EUR_USD", "XAU_USD"] # Default for now
        
        self.streamer.start_streaming(active_symbols)
        queue = await self.streamer.subscribe()
        
        try:
            while self._running:
                data = await queue.get()
                if data.get("type") == "PRICE":
                    # Forward to engine
                    await self.engine.on_tick(data)
                elif data.get("type") == "ERROR":
                    logger.error(f"LiveRunner stream error: {data.get('msg')}")
                    
        except asyncio.CancelledError:
            logger.info("LiveRunner loop cancelled")
        finally:
            self.streamer.unsubscribe(queue)

# Global instance
from app.engine import strategy_engine # We need to ensure singleton pattern
live_runner = LiveRunner(strategy_engine, price_streamer)
