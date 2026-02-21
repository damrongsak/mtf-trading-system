import json
import uuid
import redis.asyncio as redis
from src.app.core.config import settings

class TaskQueue:
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.queue_name = "queue:predictor:training"
        self.redis = None

    async def _ensure_redis(self):
        if not self.redis:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)

    async def push_training_job(self, symbol: str, lookback: int, macro_lookback: int) -> str:
        await self._ensure_redis()
        job_id = str(uuid.uuid4())
        
        payload = {
            "job_id": job_id,
            "symbol": symbol,
            "lookback": lookback,
            "macro_lookback": macro_lookback
        }
        
        # Set initial status
        await self.redis.set(f"job:{job_id}:status", "queued", ex=3600)
        
        # Push to queue
        await self.redis.lpush(self.queue_name, json.dumps(payload))
        return job_id

    async def get_job_status(self, job_id: str) -> dict:
        await self._ensure_redis()
        status = await self.redis.get(f"job:{job_id}:status")
        if not status:
            return {"job_id": job_id, "status": "not_found"}
            
        result_json = await self.redis.get(f"job:{job_id}:result")
        error = await self.redis.get(f"job:{job_id}:error")
        
        return {
            "job_id": job_id,
            "status": status,
            "result": json.loads(result_json) if result_json else None,
            "error": error
        }

task_queue = TaskQueue()
