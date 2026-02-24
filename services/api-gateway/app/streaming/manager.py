
import asyncio
import logging
from typing import Dict, Set, List
from collections import defaultdict
from fastapi import WebSocket
import json
from app.utils.redis_subscriber import RedisSubscriber
from app.streaming.handlers import MarketDataHandler
from app.streaming.feature_cache import feature_cache

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
        
        # Maps symbol to set of (websocket, source_filter) tuples
        # "EUR_USD" -> {(ws1, "OANDA"), (ws2, None)}
        self.active_connections: Dict[str, Set[tuple]] = defaultdict(set)
        self.redis = RedisSubscriber()
        self.is_running = False
        self.listen_task = None
        self.initialized = True

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for consistent matching (e.g., 'EUR_USD' -> 'EURUSD')."""
        if not symbol:
            return ""
        return symbol.replace("_", "").replace("/", "").upper()

    async def connect(self, websocket: WebSocket, symbols: List[str], source: str = None):
        """Register a new websocket connection for specific symbols."""
        await websocket.accept()
        for symbol in symbols:
            norm_symbol = self._normalize_symbol(symbol)
            self.active_connections[norm_symbol].add((websocket, source))
            
            # --- Instant Snapshot Optimization ---
            # Fetch latest price from Redis (L2 Cache) and send immediately
            try:
                # We need a redis client here. subscriber.redis is available if started.
                # However, ConnectionManager might not be started yet or we can use the same URL.
                import os
                import redis.asyncio as aioredis
                temp_redis = aioredis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)
                snapshot = await temp_redis.hgetall(f"market_data:spot:{norm_symbol}")
                await temp_redis.close()
                
                if snapshot and "bid" in snapshot:
                    logger.info(f"Sending instant snapshot for {norm_symbol} to new client")
                    # Match the format expected by the frontend (same as tick events)
                    data = {
                        "type": "PRICE",
                        "source": snapshot.get("source", "ctrader"),
                        "instrument": norm_symbol,
                        "time": snapshot.get("ts"),
                        "bid": float(snapshot["bid"]),
                        "ask": float(snapshot["ask"]),
                        "status": "tradeable"
                    }
                    await websocket.send_text(json.dumps(data))
            except Exception as e:
                logger.warning(f"Failed to send instant snapshot for {norm_symbol}: {e}")
                
        logger.info(f"Client connected. Active symbols: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket, symbols: List[str]):
        """Unregister a websocket connection."""
        for symbol in symbols:
            norm_symbol = self._normalize_symbol(symbol)
            if norm_symbol in self.active_connections:
                # Need to find and remove the tuple containing this websocket
                to_remove = set()
                for conn in self.active_connections[norm_symbol]:
                    if conn[0] == websocket:
                        to_remove.add(conn)
                
                for item in to_remove:
                    self.active_connections[norm_symbol].remove(item)

                if not self.active_connections[norm_symbol]:
                    del self.active_connections[norm_symbol]
        logger.info(f"Client disconnected. Active symbols: {len(self.active_connections)}")

    async def broadcast(self, symbol: str, message_data: str):
        """Send message to all websockets subscribed to this symbol."""
        norm_symbol = self._normalize_symbol(symbol)
        if norm_symbol not in self.active_connections:
            return

        # Parse message once if it's a string, to avoid redundant parsing in the subscriber loop
        parsed_message = None
        if isinstance(message_data, str):
            try:
                parsed_message = json.loads(message_data)
            except json.JSONDecodeError:
                pass
        else:
            parsed_message = message_data

        # Create a copy to avoid runtime errors if set changes during iteration
        for connection, source_filter in list(self.active_connections[norm_symbol]):
            try:
                # Filter logic
                # 1. If client requested specific source (source_filter is set), ONLY send matching source
                # 2. If client didn't specify (source_filter is None), send EVERYTHING
                
                msg_source = parsed_message.get("source") if isinstance(parsed_message, dict) else None
                
                if source_filter:
                    if not msg_source or msg_source.upper() != source_filter.upper():
                        continue
                
                await connection.send_text(message_data if isinstance(message_data, str) else json.dumps(message_data))
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")

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
            await self.redis.psubscribe("market_data:info:*")
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
                    if "market_data:tick:" in channel or "market_data:info:" in channel:
                        symbol = channel.split(":")[-1]
                        if "tick:" in channel:
                            logger.debug(f"Broadcasting tick for {symbol}")
                    elif "market.features." in channel:
                        symbol = channel.split(".")[-1]
                        # Populate Feature Cache
                        try:
                            features = json.loads(data)
                            feature_cache.update(symbol, features)
                        except Exception as ce:
                            logger.error(f"Failed to cache features for {symbol}: {ce}")
                    
                    if symbol:
                        await self.broadcast(symbol, data)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

# Global instance
stream_manager = ConnectionManager()
