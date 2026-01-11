
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
        # Subscribe to ticks and features
        logger.info("StreamManager: Attempting to psubscribe to market_data:tick:* and market.features.*")
        try:
            await self.redis.psubscribe("market_data:tick:*")
            await self.redis.psubscribe("market.features.*")
            logger.info("StreamManager: PSubscribed successfully.")
        except Exception as e:
            logger.error(f"StreamManager: PSubscribe FAILED: {e}")

        async for msg in self.redis.listen():
            logger.debug(f"StreamManager received redis msg: {msg}")
            if msg["type"] == "pmessage": # pattern message
                # channel examples: 
                # "market_data:tick:EUR_USD"
                # "market.features.EUR_USD"
                
                channel = msg["channel"]
                data = msg["data"]
                
                # Extract symbol logic
                try:
                    symbol = None
                    if "market_data:tick:" in channel:
                        symbol = channel.split(":")[-1]
                    elif "market.features." in channel:
                        symbol = channel.split(".")[-1]
                    
                    if symbol:
                        await self.broadcast(symbol, data)
                except Exception as e:
                    logger.error(f"Error broadcasting message: {e}")

# Global instance
stream_manager = ConnectionManager()
