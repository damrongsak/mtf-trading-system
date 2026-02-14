import json
import logging
from typing import Callable, Awaitable
from app.streaming.client import RedisStreamClient

logger = logging.getLogger(__name__)

class MarketFeatureConsumer(RedisStreamClient):
    """
    Specialized consumer for the 'market.alpha.stream'.
    Parses 'features_calculated' events.
    """
    def __init__(self, redis_url: str, group_name: str = "ai_analyst_group", consumer_name: str = "feature_worker"):
        super().__init__(
            redis_url=redis_url,
            stream_key="market.alpha.stream",
            group_name=group_name,
            consumer_name=consumer_name
        )
        self.handler: Callable[[dict], Awaitable[None]] = None

    def register_handler(self, handler: Callable[[dict], Awaitable[None]]):
        """Registers an async function to process parsed features."""
        self.handler = handler

    async def start(self):
        """Starts consumption loop."""
        await self.connect()
        logger.info("MarketFeatureConsumer started.")
        
        async for message_id, raw_data in self.consume():
            try:
                # 1. Check Event Type
                event_type = raw_data.get("event_type")
                if event_type != "features_calculated":
                    # Ack known but irrelevant messages to clear backlog
                    await self.ack(message_id)
                    continue

                # 2. Parse Payload
                if "features" in raw_data:
                    # 'features' is a JSON string inside the stream field
                    feature_data = json.loads(raw_data["features"])
                    
                    # 3. Invoke Handler
                    if self.handler:
                        await self.handler(feature_data)
                
                # 4. Ack
                await self.ack(message_id)

            except Exception as e:
                logger.error(f"Error processing message {message_id}: {e}")
                # Optional: DLQ logic here
                # Optional: DLQ logic here

class TradeEventConsumer(RedisStreamClient):
    """
    Consumer for 'market.trade.stream'.
    Updates Equity Curve Read Model.
    """
    def __init__(self, redis_url: str, group_name: str = "ai_analyst_trade_group", consumer_name: str = "equity_guardian"):
        super().__init__(
            redis_url=redis_url,
            stream_key="market.trade.stream",
            group_name=group_name,
            consumer_name=consumer_name
        )
        self.handler: Callable[[dict], Awaitable[None]] = None

    def register_handler(self, handler: Callable[[dict], Awaitable[None]]):
        self.handler = handler

    async def start(self):
        await self.connect()
        logger.info("TradeEventConsumer started.")
        
        async for message_id, raw_data in self.consume():
            try:
                event_type = raw_data.get("event_type")
                if event_type != "trade_closed":
                    await self.ack(message_id)
                    continue

                # raw_data is flat dict of strings
                if self.handler:
                    # Construct a structured object/dict expected by update_curve
                    trade_data = {
                        "id": raw_data.get("trade_id", "unknown"),
                        "pnl": float(raw_data.get("pnl", 0.0)),
                        "close_time": raw_data.get("close_time"),
                        "symbol": raw_data.get("symbol"),
                        "account_id": raw_data.get("account_id")
                    }
                    await self.handler(trade_data)
                
                await self.ack(message_id)

            except Exception as e:
                logger.error(f"Error processing trade event {message_id}: {e}")
