import asyncio
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Awaitable

from app.core.app_config import config
from app.core.logger import get_logger
from app.tools.falkordb_client import FalkorDBClient

logger = get_logger("OlympusOrchestrator")


class TaskOrchestrator:
    """
    Institutional-grade Task Orchestrator for Knowledge Ingestion.
    Supports:
    - Managed parallel execution (Semaphore)
    - Batch-id tracking
    - Granular progress reporting via Redis Pub/Sub
    - Cross-worker persistence
    """

    def __init__(self):
        self._semaphore = None
        self.client = FalkorDBClient(host=config.falkor_host, port=config.falkor_port)
        self.prefix = "task:"
        self.batch_prefix = "batch:"
        self.queue_name = "queue:ingestion"
        self.expiry = 86400  # 24 hours

    def _get_redis(self):
        """Unified Redis access. Note: connect() is synchronous but uses a 10s timeout."""
        if not self.client._client:
            self.client.connect()
        return self.client._client

    async def register_task(self, filename: str, batch_id: Optional[str] = None) -> str:
        """Register a new task in the store and push to the persistent queue."""
        task_id = str(uuid.uuid4())
        payload = {
            "task_id": task_id,
            "filename": filename,
            "batch_id": batch_id,
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "stage": "queued",
        }

        def _execute():
            r = self._get_redis()
            if r:
                # 1. Store task metadata
                r.set(f"{self.prefix}{task_id}", json.dumps(payload), ex=self.expiry)
                # 2. Add to batch if needed
                if batch_id:
                    r.sadd(f"{self.batch_prefix}{batch_id}", task_id)
                    r.expire(f"{self.batch_prefix}{batch_id}", self.expiry)
                # 3. Push to PERSISTENT QUEUE (RPUSH)
                r.rpush(self.queue_name, task_id)
                # 4. Notify listeners
                r.publish(
                    f"progress:{task_id}",
                    json.dumps(
                        {"stage": "queued", "task_id": task_id, "filename": filename}
                    ),
                )
                return True
            return False

        success = await asyncio.to_thread(_execute)
        if not success:
            logger.error(f"❌ Failed to register task {task_id} in Redis")

        return task_id

    async def get_next_task(self, timeout: int = 5) -> Optional[str]:
        """Pull the next task ID from the persistent queue (BLPOP)."""

        def _execute():
            r = self._get_redis()
            if not r:
                return None
            # BLPOP returns (queue_name, value) or None
            # result[1] is already decoded because decode_responses=True in FalkorDBClient
            result = r.blpop(self.queue_name, timeout=timeout)
            return result[1] if result else None

        return await asyncio.to_thread(_execute)

    async def get_queue_depth(self) -> int:
        """Get the number of pending tasks in the queue."""

        def _execute():
            r = self._get_redis()
            if not r:
                return 0
            return r.llen(self.queue_name)

        return await asyncio.to_thread(_execute)

    async def update_progress(
        self,
        task_id: str,
        stage: str,
        detail: Optional[str] = None,
        percentage: float = 0.0,
    ):
        """Update task progress and publish SSE event via threads."""

        def _execute():
            r = self._get_redis()
            if not r:
                return
            data_raw = r.get(f"{self.prefix}{task_id}")
            if data_raw:
                data = json.loads(data_raw)
                data["status"] = "processing"
                data["stage"] = stage
                data["detail"] = detail
                data["percentage"] = percentage
                data["updated_at"] = datetime.now().isoformat()
                r.set(f"{self.prefix}{task_id}", json.dumps(data), ex=self.expiry)
                event = {
                    "task_id": task_id,
                    "stage": stage,
                    "detail": detail,
                    "percentage": percentage,
                    "ts": datetime.now().isoformat(),
                }
                r.publish(f"progress:{task_id}", json.dumps(event))

        await asyncio.to_thread(_execute)

    async def finalize_task(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        """Mark task as complete or failed via threads."""

        def _execute():
            r = self._get_redis()
            if not r:
                return
            data_raw = r.get(f"{self.prefix}{task_id}")
            if data_raw:
                data = json.loads(data_raw)
                data["status"] = status
                data["stage"] = (
                    "pipeline_done" if status == "completed" else "pipeline_failed"
                )
                data["result"] = result
                data["error"] = error
                data["finished_at"] = datetime.now().isoformat()
                data["updated_at"] = datetime.now().isoformat()
                r.set(f"{self.prefix}{task_id}", json.dumps(data), ex=self.expiry)
                event = {
                    "task_id": task_id,
                    "stage": data["stage"],
                    "status": status,
                    "result": result,
                    "error": error,
                    "ts": datetime.now().isoformat(),
                }
                r.publish(f"progress:{task_id}", json.dumps(event))

        await asyncio.to_thread(_execute)

    async def run_managed(
        self, task_id: str, coro_func: Callable[..., Awaitable[Any]], *args, **kwargs
    ):
        """Execute a coroutine within the concurrency limit (semaphore)."""
        if self._semaphore is None:
            self._semaphore = asyncio.BoundedSemaphore(
                getattr(config, "ki_max_concurrency", 5)
            )

        async with self._semaphore:
            logger.info(f"🟢 Semaphore acquired: Task {task_id} entering pool.")
            try:
                await self.update_progress(
                    task_id, stage="processing", detail="Acquired worker slot"
                )
                return await coro_func(task_id, *args, **kwargs)
            except Exception as e:
                logger.error(f"❌ Orchestrated task {task_id} failed in pool: {e}")
                await self.finalize_task(task_id, status="failed", error=str(e))
                raise

    def get_batch_stats(self, batch_id: str) -> Dict[str, Any]:
        """Aggregate stats for a specific batch."""
        r = self._get_redis()
        if not r:
            return {"error": "Redis not connected"}

        task_ids = r.smembers(f"{self.batch_prefix}{batch_id}")
        if not task_ids:
            return {"batch_id": batch_id, "total": 0, "status": "not_found"}

        stats: Dict[str, Any] = {
            "batch_id": batch_id,
            "total": len(task_ids),
            "queued": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "skipped": 0,
            "nodes_created": 0,
            "edges_created": 0,
            "tasks": [],
        }

        for tid in task_ids:
            tdata_raw = r.get(f"{self.prefix}{tid}")
            if tdata_raw:
                tdata = json.loads(tdata_raw)
                status = tdata.get("status", "unknown")
                stats[status] = stats.get(status, 0) + 1

                # Accumulate graph stats
                result = tdata.get("result", {})
                stats["nodes_created"] += result.get("total_nodes", 0)
                stats["edges_created"] += result.get("total_edges", 0)

                stats["tasks"].append(
                    {
                        "task_id": tid,
                        "filename": tdata.get("filename"),
                        "status": status,
                        "stage": tdata.get("stage"),
                    }
                )

        return stats

    def get_global_stats(self) -> Dict[str, Any]:
        """Get aggregate metrics for the entire service."""
        r = self._get_redis()
        if not r:
            return {"error": "Redis not connected"}

        keys = r.keys(f"{self.prefix}*")
        stats = {
            "global": {
                "total_tasks_last_24h": len(keys),
                "active_concurrency": getattr(
                    self._semaphore, "_value", config.ki_max_concurrency
                )
                if self._semaphore
                else config.ki_max_concurrency,
                "max_concurrency": config.ki_max_concurrency,
            },
            "statuses": {
                "queued": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
                "skipped": 0,
            },
        }

        for k in keys:
            tdata_raw = r.get(k)
            if tdata_raw:
                try:
                    tdata = json.loads(tdata_raw)
                    status = tdata.get("status", "unknown")
                    if status in stats["statuses"]:
                        stats["statuses"][status] += 1
                except Exception:
                    pass

        return stats


# Singleton instance
orchestrator = TaskOrchestrator()
