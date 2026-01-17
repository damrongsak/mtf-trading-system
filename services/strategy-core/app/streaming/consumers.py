import json
import logging
from typing import Callable, Awaitable
from app.streaming.client import RedisStreamClient

logger = logging.getLogger(__name__)

class MarketFeatureConsumer(RedisStreamClient):
    """
    Consumes 'features_calculated' events from 'market.alpha.stream'.
    """
    def __init__(self, redis_url: str, group_name: str = "strategy_core_group", consumer_name: str = "feature_listener"):
        super().__init__(
            redis_url=redis_url,
            stream_key="market.alpha.stream",
            group_name=group_name,
            consumer_name=consumer_name
        )
        self.handler: Callable[[dict], Awaitable[None]] = None

    def register_handler(self, handler: Callable[[dict], Awaitable[None]]):
        self.handler = handler

    async def start(self):
        await self.connect()
        logger.info("MarketFeatureConsumer started.")
        
        async for message_id, raw_data in self.consume():
            try:
                if raw_data.get("event_type") == "features_calculated" and "features" in raw_data:
                    feature_data = json.loads(raw_data["features"])
                    if self.handler:
                        await self.handler(feature_data)
                
                await self.ack(message_id)

            except Exception as e:
                logger.error(f"Error processing feature {message_id}: {e}")

class CandleConsumer(RedisStreamClient):
    """
    Consumes 'candle_completed' events from 'market.data.stream'.
    Useful for IndicatorWorker replacement.
    """
    def __init__(self, redis_url: str, group_name: str = "indicator_group", consumer_name: str = "worker_1"):
        super().__init__(
            redis_url=redis_url,
            stream_key="market.data.stream",
            group_name=group_name,
            consumer_name=consumer_name
        )
        self.handler: Callable[[str, dict], Awaitable[None]] = None

    def register_handler(self, handler: Callable[[str, dict], Awaitable[None]]):
        """Handler signature: (message_id, fields)"""
        self.handler = handler

    async def start(self):
        await self.connect()
        logger.info("CandleConsumer started.")
        
        async for message_id, fields in self.consume():
            try:
                if fields.get("event_type") == "candle_completed":
                    if self.handler:
                        await self.handler(message_id, fields)
                    else:
                        # If no handler, we still ack? Or maybe we assume manual ack.
                        # The client/consumer pattern usually implies automatic ack if handler succeeds.
                        # But IndicatorWorker needs manual control sometimes?
                        # Let's simple ack.
                        await self.ack(message_id)
                else:
                    await self.ack(message_id) # Ack irrelevant events

            except Exception as e:
                logger.error(f"Error processing candle {message_id}: {e}")
