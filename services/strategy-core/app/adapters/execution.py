import os
import json
import redis.asyncio as redis
from typing import Dict, Any

EXECUTION_SERVICE_URL = os.getenv("EXECUTION_SERVICE_URL", "http://execution:8000")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

class ExecutionClient:
    def __init__(self):
        self.base_url = EXECUTION_SERVICE_URL
        self.redis_url = REDIS_URL
        self.queue_name = "queue:execution:commands"
        self._redis = None
        
    async def _get_redis(self):
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place an order via Redis Queue (Async RPC).
        """
        try:
            r = await self._get_redis()
            await r.lpush(self.queue_name, json.dumps(order_data))
            return {"status": "queued", "queue": self.queue_name}
        except Exception as e:
            # If error, clear redis connection to retry next time
            self._redis = None
            print(f"Redis Queue Error: {e}")
            raise

execution_client = ExecutionClient()
