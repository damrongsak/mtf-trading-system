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
        self.priority_queue = "queue:execution:priority"
        self.default_queue = "queue:execution:commands"
        self.max_queue_size = int(os.getenv("EXECUTION_MAX_QUEUE_SIZE", "100"))
        self._redis = None
        
    async def _get_redis(self):
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place an order via Redis Queue (Async RPC).
        Prioritizes Close/Modify commands.
        """
        try:
            import time
            # Nanosecond precision for HFT-lite latency tracking
            order_data["signal_timestamp_ns"] = time.time_ns()
            
            r = await self._get_redis()
            
            # Determine priority
            cmd_type = order_data.get("type", "OPEN").upper()
            is_priority = cmd_type in ["CLOSE", "MODIFY", "CANCEL", "EXIT"]
            target_queue = self.priority_queue if is_priority else self.default_queue

            # Circuit Breaker: Check Queue Length (Allow priority queue to grow larger)
            limit = self.max_queue_size * 2 if is_priority else self.max_queue_size
            queue_len = await r.llen(target_queue)
            
            if queue_len >= limit:
                raise Exception(f"CIRCUIT BREAKER: {target_queue} is full ({queue_len}/{limit}). Order dropped.")
                
            await r.lpush(target_queue, json.dumps(order_data))
            return {"status": "queued", "queue": target_queue}
        except Exception as e:
            # If error, clear redis connection to retry next time
            self._redis = None
            print(f"Redis Queue Error: {e}")
            raise
    async def update_quotes(self, **kwargs) -> Dict[str, Any]:
        """
        Update Bid/Ask quotes via Redis Priority Queue.
        """
        try:
            r = await self._get_redis()
            payload = {
                "type": "update_quotes",
                **kwargs
            }
            # Quotes updates are high priority for risk management accuracy
            await r.lpush(self.priority_queue, json.dumps(payload))
            return {"status": "queued", "command": "update_quotes", "queue": self.priority_queue}
        except Exception as e:
            self._redis = None
            print(f"Redis Queue Error (update_quotes): {e}")
            raise

execution_client = ExecutionClient()
