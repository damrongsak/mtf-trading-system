"""
Olympus Ingestion Worker - Persistent Task Consumer
Pulls from Redis List (queue:ingestion) and processes tasks one-by-one with concurrency limits.
"""

import asyncio
import json
from pathlib import Path

from app.core.app_config import config
from app.core.logging_config import get_logger
from app.core.orchestrator import orchestrator
from app.core.factory import get_ingestor
from app.utils.tracing import request_id_ctx

logger = get_logger("IngestionWorker")


class IngestionWorker:
    def __init__(self):
        self.is_running = False
        self._semaphore = asyncio.Semaphore(config.ki_max_concurrency)

    async def start(self):
        """Start the continuous worker loop."""
        if self.is_running:
            return
        self.is_running = True
        logger.info(
            f"🚀 Ingestion Worker started (Concurrency: {config.ki_max_concurrency})"
        )
        asyncio.create_task(self._loop())

    async def stop(self):
        """Stop the worker loop."""
        self.is_running = False
        logger.info("🛑 Ingestion Worker stopping...")

    async def _loop(self):
        """Main consumer loop - Pulls only when concurrency slot is available."""
        while self.is_running:
            try:
                # IMPORTANT: Acquire semaphore slot BEFORE pulling from Redis
                # This prevents over-consumption and ensures tasks stay in Redis
                # until a worker is ready to process them.
                await self._semaphore.acquire()

                task_id = await orchestrator.get_next_task(timeout=5)
                if not task_id:
                    self._semaphore.release()
                    continue

                # Spawn task and handle semaphore release internally
                asyncio.create_task(self._process_task_with_release(task_id))

            except Exception as e:
                logger.error(f"❌ Worker loop error: {e}")
                await asyncio.sleep(5)

    async def _process_task_with_release(self, task_id: str):
        """Wrapper to ensure semaphore is released even if processing fails early."""
        try:
            await self._process_task_safely(task_id)
        finally:
            self._semaphore.release()

    async def _process_task_safely(self, task_id: str):
        """Process a single task (semaphore managed by caller)."""
        token = request_id_ctx.set(task_id)
        try:
            # 1. Fetch task metadata from Redis
            r = orchestrator._get_redis()
            data_raw = r.get(f"{orchestrator.prefix}{task_id}")
            if not data_raw:
                logger.warning(
                    f"⚠️ Task {task_id} not found in metadata store. Skipping."
                )
                return

            task_data = json.loads(data_raw)
            filename = task_data.get("filename")
            task_data.get("batch_id")

            # Resolve file path
            # Try source_dir first, then check common locations
            file_path = Path(config.source_dir) / filename
            if not file_path.exists():
                # Check if it's already an absolute path stored in filename (e.g. from directory ingest)
                file_path = Path(filename)
                if not file_path.exists():
                    logger.error(f"❌ File not found for task {task_id}: {filename}")
                    await orchestrator.finalize_task(
                        task_id, status="failed", error="File not found"
                    )
                    return

            logger.info(f"🏗️ [WORKER] Processing Task {task_id}: {file_path.name}")
            await orchestrator.update_progress(
                task_id, stage="started", detail="Worker acquired lock"
            )

            # 2. Run the actual ingestion pipeline
            ingest_svc = get_ingestor()
            # pipeline uses force/task_id from orchestrated state if needed
            result = await ingest_svc.run_pipeline(file_path, task_id=task_id)

            # 3. Finalize
            final_status = "completed" if result.status == "complete" else "failed"
            if result.status == "complete":
                ingest_svc.archive_file(file_path)
            else:
                reason = result.error or "Pipeline failure"
                ingest_svc.move_to_errors(file_path, reason)

            await orchestrator.finalize_task(
                task_id, status=final_status, result=result.model_dump()
            )
            logger.info(f"✅ [WORKER] Task {task_id} finished: {final_status}")

        except Exception as e:
            logger.error(f"❌ [WORKER] Fatal error in task {task_id}: {e}")
            await orchestrator.finalize_task(task_id, status="failed", error=str(e))
        finally:
            request_id_ctx.reset(token)


# Singleton worker instance
worker = IngestionWorker()
