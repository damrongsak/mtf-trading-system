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
        self.max_queue_size = int(os.getenv("EXECUTION_MAX_QUEUE_SIZE", "50"))
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
            
            # Circuit Breaker: Check Queue Length
            queue_len = await r.llen(self.queue_name)
            if queue_len >= self.max_queue_size:
                raise Exception(f"CIRCUIT BREAKER: Execution queue is full ({queue_len}/{self.max_queue_size}). Order dropped.")
                
            await r.lpush(self.queue_name, json.dumps(order_data))
            return {"status": "queued", "queue": self.queue_name}
        except Exception as e:
            # If error, clear redis connection to retry next time
            self._redis = None
            print(f"Redis Queue Error: {e}")
            raise
    async def update_quotes(self, **kwargs) -> Dict[str, Any]:
        """
        Update Bid/Ask quotes via Redis Queue.
        """
        try:
            r = await self._get_redis()
            payload = {
                "type": "update_quotes",
                **kwargs
            }
            await r.lpush(self.queue_name, json.dumps(payload))
            return {"status": "queued", "command": "update_quotes"}
        except Exception as e:
            self._redis = None
            print(f"Redis Queue Error (update_quotes): {e}")
            raise

execution_client = ExecutionClient()
