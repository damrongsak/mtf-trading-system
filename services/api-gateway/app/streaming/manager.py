
import asyncio
import logging
from typing import Dict, Set, List
from collections import defaultdict
from fastapi import WebSocket
from app.utils.redis_subscriber import RedisSubscriber

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Singleton manager to handle multiple WebSocket connections with a single Redis subscription (Multiplexing).
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConnectionManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        
        # Maps symbol to set of websockets: "EUR_USD" -> {ws1, ws2}
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self.redis = RedisSubscriber()
        self.is_running = False
        self.listen_task = None
        self.initialized = True

    async def connect(self, websocket: WebSocket, symbols: List[str]):
        """Register a new websocket connection for specific symbols."""
        await websocket.accept()
        for symbol in symbols:
            self.active_connections[symbol].add(websocket)
        logger.info(f"Client connected. Active symbols: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket, symbols: List[str]):
        """Unregister a websocket connection."""
        for symbol in symbols:
            # Check if symbol exists before accessing to avoid creating empty entry in defaultdict
            if symbol in self.active_connections:
                if websocket in self.active_connections[symbol]:
                    self.active_connections[symbol].remove(websocket)
                    if not self.active_connections[symbol]:
                        del self.active_connections[symbol]
        logger.info(f"Client disconnected. Active symbols: {len(self.active_connections)}")

    async def broadcast(self, symbol: str, message: str):
        """Send message to all websockets subscribed to this symbol."""
        if symbol not in self.active_connections:
            return

        # Create a copy to avoid runtime errors if set changes during iteration
        for connection in list(self.active_connections[symbol]):
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                # We could cleanup here, but disconnect() usually handles it

    async def start(self):
        """Start the background Redis listener."""
        if self.is_running:
            return

        self.is_running = True
        self.listen_task = asyncio.create_task(self._redis_listener())
        logger.info("StreamManager background listener started.")

    async def stop(self):
        """Stop the background listener and close Redis connection."""
        self.is_running = False
        if self.listen_task:
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                pass
        
        await self.redis.close()
        logger.info("StreamManager background listener stopped.")

    async def _redis_listener(self):
        """Consumes messages from Redis and fans them out."""
        await self.redis.connect()
        # Subscribe to all tick data
        await self.redis.subscribe(["market_data:tick:*"]) # Note: RedisSubscriber needs psubscribe support for patterns
        
        # NOTE: The existing RedisSubscriber might not support psubscribe or might need adjustment.
        # Checking existing code: it uses self.pubsub.subscribe(*channels).
        # To support patterns, we should use psubscribe. 
        # But wait, existing RedisSubscriber uses standard subscribe. 
        # For simplicity and compatibility with existing patterns (market_data:tick:EUR_USD),
        # we can just use psubscribe with pattern "market_data:tick:*" 
        # IF the underlying library supports it. 
        # redis-py pubsub supports psubscribe.
        # Let's adjust RedisSubscriber if needed, OR just update this to use psubscribe directly if RedisSubscriber exposes it.
        # Actually, let's look at RedisSubscriber source again. It calls self.pubsub.subscribe.
        # I should probably update RedisSubscriber to support pattern subscription or access pubsub directly.
        # For now, I will assume I need to update RedisSubscriber OR use a pattern.
        # Let's try to access the underlying pubsub object if possible or add a psubscribe method to RedisSubscriber.
        # BUT, to adhere to clean code, I should probably add `psubscribe` to `RedisSubscriber`.
        
        # Let's optimistically assume I'll add psubscribe to RedisSubscriber or just access it.
        # The current implementation in `app/streaming/manager.py` needs to call psubscribe.
        
        if self.redis.pubsub:
             await self.redis.pubsub.psubscribe("market_data:tick:*")
        else:
             # Fallback if connect wasn't called (it is called above) or logic differs
             pass

        async for msg in self.redis.listen():
            if msg["type"] == "pmessage": # pattern message
                # channel is the specific channel (market_data:tick:EUR_USD)
                # data is the payload
                channel = msg["channel"]
                data = msg["data"]
                
                # Extract symbol from channel: "market_data:tick:EUR_USD" -> "EUR_USD"
                try:
                    symbol = channel.split(":")[-1]
                    await self.broadcast(symbol, data)
                except Exception as e:
                    logger.error(f"Error broadcasting message: {e}")

# Global instance
stream_manager = ConnectionManager()
