import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional
from redis.asyncio import Redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class StateCache:
    """
    Singleton cache that maintains a local copy of system state (ECST).
    Subscribes to 'state_updates' channel to keep in-memory data fresh.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StateCache, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        
        self._data: Dict[str, Any] = {}
        self._redis_url = settings.REDIS_URL
        self._is_running = False
        self._listen_task: Optional[asyncio.Task] = None
        self.initialized = True

    def get(self, key: str, default: Any = None) -> Any:
        """O(1) local read."""
        return self._data.get(key, default)

    def set_local(self, key: str, value: Any):
        """Update local storage."""
        self._data[key] = value

    async def start(self):
        """Start the background Redis listener and perform initial hydration."""
        if self._is_running:
            return
        
        self._is_running = True
        
        # Initial Hydration (Optional: Load important keys from Redis at startup)
        # For now, we'll rely on events and on-demand fetch if needed, 
        # but ECST usually thrives on 'Event-Carried' payloads.
        
        self._listen_task = asyncio.create_task(self._redis_listener())
        logger.info("🚀 StateCache (ECST) background listener started.")

    async def stop(self):
        """Stop the listener."""
        self._is_running = False
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 StateCache (ECST) background listener stopped.")

    async def _redis_listener(self):
        """Listens for state_updates and updates local memory."""
        redis = Redis.from_url(self._redis_url, decode_responses=True)
        pubsub = redis.pubsub()
        
        try:
            await pubsub.subscribe("state_updates")
            logger.info("✅ StateCache subscribed to 'state_updates' channel.")
            
            while self._is_running:
                try:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message["type"] == "message":
                        payload = json.loads(message["data"])
                        key = payload.get("key")
                        value = payload.get("value")
                        
                        if key:
                            self.set_local(key, value)
                            logger.info(f"ECST: Updated local cache for {key}")
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error in StateCache listener loop: {e}")
                    await asyncio.sleep(1)
        finally:
            await pubsub.unsubscribe("state_updates")
            await redis.aclose()

# Global instance
state_cache = StateCache()
