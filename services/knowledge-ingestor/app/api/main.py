import shutil
import uuid
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.core.app_config import config
from app.core.logging_config import get_logger
from app.core.orchestrator import orchestrator
from app.core.factory import get_ingestor
from app.core.worker import worker
from app.utils.middleware import RequestIDMiddleware
from app.api.streaming import router as streaming_router

logger = get_logger("OlympusAPI")

app = FastAPI(
    title="Project Olympus Ingestor API",
    description="Professional Knowledge Graph Ingestion Service",
    version="1.0.0",
)
app.add_middleware(RequestIDMiddleware)
app.include_router(streaming_router, prefix="/stream", tags=["Streaming"])


# ────────────────────────── Schemas ──────────────────────────────────────────
class DirectoryIngestRequest(BaseModel):
    path: str
    force: bool = False
    clean_first: bool = False


class UrlRequest(BaseModel):
    url: str


# ────────────────────────── Startup / Health ─────────────────────────────────


@app.on_event("startup")
async def startup_event():
    """Fast-boot: Ensure worker starts immediately without blocking infrastructure checks."""
    logger.info("🏛️ Project Olympus Ingestor: READY")
    # Start the persistent worker
    await worker.start()


@app.get("/health")
async def health_check():
    """Basic health endpoint for monitoring."""
    return {"status": "healthy", "service": "app-ingestor", "version": "1.0.0"}


@app.get("/health/llm", tags=["Health"])
async def llm_health_check():
    """Professional 3-Tier LLM Health Check."""
    from app.core.health import _check_openrouter_model, _check_gemini_direct

    results = await asyncio.gather(
        asyncio.to_thread(_check_openrouter_model, config.tier1_model, "tier1"),
        asyncio.to_thread(_check_openrouter_model, config.tier2_model, "tier2"),
        asyncio.to_thread(_check_gemini_direct, config.tier3_model, "tier3"),
    )

    healthy_count = sum(1 for r in results if r["status"] == "healthy")
    return {
        "overall_status": "healthy" if healthy_count > 0 else "degraded",
        "healthy_tiers": healthy_count,
        "tiers": results,
    }


# ────────────────────────── Endpoints ────────────────────────────────────────


@app.post("/ingest", status_code=202)
async def ingest_file(file: UploadFile = File(...)):
    """Upload a file and trigger asynchronous ingestion via persistent queue."""
    task_id = await orchestrator.register_task(file.filename or "unknown_file")
    temp_path = Path(config.source_dir) / f"{task_id}_{file.filename}"

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"📥 Queued file for ingestion: {file.filename} (Task: {task_id})")
    except Exception as e:
        await orchestrator.finalize_task(task_id, status="failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"File save failed: {e}")

    return {"task_id": task_id, "status": "queued", "filename": file.filename}


@app.post("/ingest/batch", status_code=202)
async def ingest_batch(files: List[UploadFile] = File(...)):
    """Upload multiple files and trigger asynchronous ingestion via persistent queue."""
    batch_id = str(uuid.uuid4())
    task_ids = []

    for file in files:
        task_id = await orchestrator.register_task(file.filename or f"file_{uuid.uuid4().hex[:8]}", batch_id=batch_id)
        temp_path = Path(config.source_dir) / f"{task_id}_{file.filename}"
        try:
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            task_ids.append({"task_id": task_id, "filename": file.filename})
        except Exception:
            await orchestrator.finalize_task(
                task_id, status="failed", error="Save failed"
            )
            continue

    logger.info(f"📥 Queued batch of {len(task_ids)} files (Batch: {batch_id})")
    return {"batch_id": batch_id, "tasks": task_ids}


@app.post("/ingest/directory", status_code=202)
async def ingest_directory(request: DirectoryIngestRequest):
    """Trigger bulk ingestion from a local server directory via persistent queue."""
    target_path = Path(request.path)
    if not target_path.exists():
        target_path = Path("/app") / request.path
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Directory not found")

    ingest_svc = get_ingestor()
    if request.clean_first:
        await asyncio.to_thread(ingest_svc.client.delete_graph)

    extensions = {".md", ".pdf", ".txt", ".markdown"}
    files = []
    for f in target_path.glob("**/*"):
        if f.is_file() and f.suffix.lower() in extensions:
            files.append(f)

    batch_id = str(uuid.uuid4())
    task_ids = []
    for file_path in files:
        # Register task (this automatically RPUSHes to Redis queue)
        task_id = await orchestrator.register_task(str(file_path), batch_id=batch_id)
        task_ids.append({"task_id": task_id, "filename": file_path.name})

    logger.info(
        f"📥 Queued {len(files)} files from directory {request.path} (Batch: {batch_id})"
    )
    return {"batch_id": batch_id, "total_files": len(files), "tasks": task_ids}


@app.post("/ingest/url", status_code=202)
async def ingest_url(request: UrlRequest):
    """Provide a URL to scrape and ingest its content via persistent queue."""
    # Registering a URL task also goes through the queue
    # NOTE: The worker will need to know how to handle scrape-then-ingest
    task_id = await orchestrator.register_task(request.url)
    logger.info(f"📥 Queued URL for ingestion: {request.url} (Task: {task_id})")
    return {"task_id": task_id, "status": "queued"}


@app.get("/status/{task_id}")
async def get_status(task_id: str):
    """Get the status of a specific ingestion task."""
    r = await asyncio.to_thread(orchestrator._get_redis)
    data = await asyncio.to_thread(r.get, f"task:{task_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Task not found")
    return json.loads(data)


@app.get("/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    """Detailed stats for an entire batch ingestion."""
    stats = await asyncio.to_thread(orchestrator.get_batch_stats, batch_id)
    if stats.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Batch not found")
    return stats


@app.get("/stats")
async def get_global_stats():
    """Service-wide ingestion metrics dashboard."""
    return await asyncio.to_thread(orchestrator.get_global_stats)


@app.get("/tasks")
async def list_tasks():
    """List all recent ingestion tasks."""
    r = await asyncio.to_thread(orchestrator._get_redis)
    keys = await asyncio.to_thread(r.keys, "task:*")
    tasks = []
    for k in keys:
        val = await asyncio.to_thread(r.get, k)
        if val:
            tasks.append(json.loads(val))
    return tasks


# ────────────────────────── Scheduled Workers ────────────────────────────────


async def start_background_workers():
    """Initialize all non-blocking background workers."""
    from app.workers.merger import MarketMerger

    async def price_refresher():
        from app.tools.market_reader import MarketReaderTool
        from app.tools.falkordb_client import FalkorDBClient

        client = FalkorDBClient(host=config.falkor_host, port=config.falkor_port)
        assets = ["Gold", "Bitcoin", "Silver", "Crude Oil", "S&P 500"]

        while True:
            r = await asyncio.to_thread(orchestrator._get_redis)
            lock_key = "lock:asset_price_refresher"
            if await asyncio.to_thread(r.set, lock_key, "1", nx=True, ex=3500):
                try:
                    for asset in assets:
                        # MarketReaderTool.get_spot_price IS ALREADY ASYNC.
                        # DO NOT wrap it in asyncio.to_thread.
                        price = await MarketReaderTool.get_spot_price(asset)
                        if price:
                            now_str = datetime.now().isoformat()
                            query = f"MERGE (a:Asset {{name: '{asset}'}}) SET a.price = {price}, a.last_updated = '{now_str}'"
                            # GraphQL execute_query handles its own threading or is async
                            await asyncio.to_thread(client.execute_query, query)
                except Exception as e:
                    logger.error(f"❌ Price refresher error: {e}")
            await asyncio.sleep(3600)

    async def merger_loop():
        r = await asyncio.to_thread(orchestrator._get_redis)
        while True:
            lock_key = "lock:market_merger"
            if await asyncio.to_thread(r.set, lock_key, "1", nx=True, ex=1700):
                try:
                    merger = MarketMerger()
                    await merger.seed_baseline()
                    await merger.merge_market_sentiment()
                except Exception:
                    pass
            await asyncio.sleep(600)

    asyncio.create_task(price_refresher())
    asyncio.create_task(merger_loop())


@app.on_event("startup")
async def register_background_workers():
    """Hook to start loops after app initialization."""
    await start_background_workers()
