import os
import shutil
import uuid
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.core.app_config import config
from app.core.logger import get_logger
from app.core.health import StartupGuard
from app.ingestors.hierarchical_ingestor import HierarchicalIngestor
from app.core.graph_linter import GraphLinter
from app.utils.middleware import RequestIDMiddleware
from app.utils.tracing import request_id_ctx
from app.tools.falkordb_client import FalkorDBClient

logger = get_logger("OlympusAPI")

app = FastAPI(
    title="Project Olympus Ingestor API",
    description="Professional Knowledge Graph Ingestion Service",
    version="1.0.0"
)
app.add_middleware(RequestIDMiddleware)

# Global Ingestor & Linter Instances
ingestor = HierarchicalIngestor()
linter = GraphLinter()

# --- Redis-Backed Task Store (Fix for Multi-Worker Visibility) ---
class RedisTaskStore:
    """Task storage using Redis to share state across workers."""
    def __init__(self):
        self.client = FalkorDBClient(host=config.falkor_host, port=config.falkor_port)
        self.prefix = "task:"
        self.expiry = 86400 # 24 hours
        
    def _get_redis(self):
        if not self.client._client:
            self.client.connect()
        return self.client._client

    def __setitem__(self, key, value):
        r = self._get_redis()
        if r:
            r.set(f"{self.prefix}{key}", json.dumps(value), ex=self.expiry)

    def __getitem__(self, key):
        r = self._get_redis()
        if not r: return None
        data = r.get(f"{self.prefix}{key}")
        if not data:
            raise KeyError(key)
        return json.loads(data)

    def __contains__(self, key):
        r = self._get_redis()
        return r.exists(f"{self.prefix}{key}") if r else False

    def get(self, key, default=None):
        try:
            val = self[key]
            return val if val is not None else default
        except KeyError:
            return default

    def update(self, key, **kwargs):
        data = self.get(key, {})
        data.update(kwargs)
        self[key] = data

    def all(self):
        r = self._get_redis()
        if not r: return {}
        keys = r.keys(f"{self.prefix}*")
        results = {}
        for k in keys:
            task_id = k.replace(self.prefix, "")
            try:
                results[task_id] = self[task_id]
            except:
                pass
        return results

tasks = RedisTaskStore()

class IngestionTask(BaseModel):
    task_id: str
    filename: str
    status: str
    detail: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Run health checks on startup."""
    if not StartupGuard.run_all():
        logger.critical("🛑 Startup Health Checks Failed. Exiting.")
        os._exit(1)

@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirect root to API documentation."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

@app.get("/health")
async def health_check():
    """Basic health endpoint for monitoring."""
    return {"status": "healthy", "service": "app-ingestor", "version": "1.0.0"}

async def run_ingestion_background(task_id: str, file_path: Path):
    """Background task to run the ingestion pipeline."""
    # Inherit or set task_id as correlation_id
    token = request_id_ctx.set(task_id)
    try:
        tasks.update(task_id, status="processing")
        logger.info(f"🚀 Background Task {task_id} started for {file_path.name}")
        
        result = await ingestor.run_pipeline(file_path)
        
        # Determine if it was a skip or actual completion
        final_status = "completed"
        if result.status == "complete":
            # Check if it was skipped (no nodes created and merge_notes mentions skip)
            if getattr(result, "total_nodes", 0) == 0 and "Skipped" in str(result.committer_result.get("merge_notes", "")):
                final_status = "skipped"
                logger.info(f"⏭️ Task {task_id} skipped (already exists).")
            else:
                logger.info(f"✅ Task {task_id} completed successfully.")
            
            # Archive the file
            ingestor.archive_file(file_path)
        else:
            final_status = "failed"
            reason = getattr(result, "error", "Unknown pipeline error")
            ingestor.move_to_errors(file_path, str(reason))
            logger.error(f"❌ Task {task_id} failed: {reason}")

        # Final update to Redis
        tasks.update(
            task_id, 
            status=final_status, 
            result=result.__dict__ if hasattr(result, "__dict__") else result,
            finished_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        tasks.update(task_id, status="failed", error=str(e), finished_at=datetime.now().isoformat())
        logger.error("background_task_failed", extra={"task_id": task_id, "error": str(e)})
        ingestor.move_to_errors(file_path, str(e))
    finally:
        request_id_ctx.reset(token)

@app.post("/ingest", status_code=202)
async def ingest_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload a file and trigger asynchronous ingestion."""
    task_id = str(uuid.uuid4())
    
    # Save the file temporarily
    temp_path = Path(config.source_dir) / f"{task_id}_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    
    tasks[task_id] = {
        "task_id": task_id,
        "filename": file.filename,
        "status": "queued",
        "timestamp": datetime.now().isoformat()
    }
    
    background_tasks.add_task(run_ingestion_background, task_id, temp_path)
    
    return {"task_id": task_id, "status": "queued", "filename": file.filename}

@app.post("/ingest/batch", status_code=202)
async def ingest_batch(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    """Upload multiple files and trigger asynchronous ingestion for each."""
    task_ids = []
    for file in files:
        task_id = str(uuid.uuid4())
        temp_path = Path(config.source_dir) / f"{task_id}_{file.filename}"
        try:
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            logger.error(f"Failed to save file in batch: {file.filename}, error: {e}")
            continue

        tasks[task_id] = {
            "task_id": task_id,
            "filename": file.filename,
            "status": "queued",
            "timestamp": datetime.now().isoformat()
        }
        background_tasks.add_task(run_ingestion_background, task_id, temp_path)
        task_ids.append({"task_id": task_id, "filename": file.filename})

    return {"batch_id": str(uuid.uuid4()), "tasks": task_ids}

class UrlRequest(BaseModel):
    url: str

@app.post("/ingest/url", status_code=202)
async def ingest_url(background_tasks: BackgroundTasks, request: UrlRequest):
    """Provide a URL to scrape and ingest its content."""
    from app.tools.web_scraper import WebScraperTool
    
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "task_id": task_id,
        "url": request.url,
        "status": "scraping",
        "timestamp": datetime.now().isoformat()
    }
    
    async def process_url():
        # Set task_id as correlation_id
        token = request_id_ctx.set(task_id)
        try:
            text = await WebScraperTool.scrape_url(request.url)
            if not text:
                tasks.update(task_id, status="failed", error="Failed to scrape URL or no content found")
                return

            tasks.update(task_id, status="ingesting")
            result = await ingestor.run_pipeline_on_text(text, filename=f"web_{task_id}")
            
            tasks.update(
                task_id, 
                status="completed", 
                result=result.__dict__ if hasattr(result, "__dict__") else result,
                finished_at=datetime.now().isoformat()
            )
        except Exception as e:
            tasks.update(task_id, status="failed", error=str(e), finished_at=datetime.now().isoformat())
            logger.error(f"URL Ingestion failed: {e}", extra={"task_id": task_id})
        finally:
            request_id_ctx.reset(token)

    background_tasks.add_task(process_url)
    return {"task_id": task_id, "status": "queued", "url": request.url}

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    """Get the status of a specific ingestion task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]

@app.get("/tasks")
async def list_tasks():
    """List all recent ingestion tasks."""
    return tasks.all()

@app.post("/graph/lint")
async def trigger_linting(background_tasks: BackgroundTasks):
    """Trigger a manual graph linting and entity resolution cycle."""
    task_id = f"lint-{uuid.uuid4().hex[:8]}"
    
    async def run_lint():
        token = request_id_ctx.set(task_id)
        try:
            await linter.run_linting_cycle()
        finally:
            request_id_ctx.reset(token)
            
    background_tasks.add_task(run_lint)
    return {"task_id": task_id, "status": "triggered", "message": "Graph linting started in background"}

# --- Background Scheduler for Asset Prices (with Distributed Locking) ---
async def asset_price_refresher():
    """Background loop to update top asset prices every hour."""
    from app.tools.market_reader import MarketReaderTool
    from app.tools.falkordb_client import FalkorDBClient
    from app.core.app_config import config
    
    client = FalkorDBClient(host=config.falkor_host, port=config.falkor_port, graph_name=config.graph_name)
    assets = ["Gold", "Bitcoin", "Silver", "Crude Oil", "S&P 500"]
    
    while True:
        # Distributed Lock to ensure only one worker runs this
        r = tasks._get_redis()
        if not r: 
            await asyncio.sleep(60)
            continue
            
        # Try to acquire lock for 1 hour
        lock_key = "lock:asset_price_refresher"
        if r.set(lock_key, "1", nx=True, ex=3500):
            cycle_id = f"refresh-{uuid.uuid4().hex[:8]}"
            token = request_id_ctx.set(cycle_id)
            logger.info("🕒 Starting scheduled asset price refresh (Lock Acquired)...")
            try:
                for asset in assets:
                    price = MarketReaderTool.get_spot_price(asset)
                    if price:
                        now_str = datetime.now().isoformat()
                        query = f"MERGE (a:Asset {{name: '{asset}'}}) SET a.price = {price}, a.last_updated = '{now_str}'"
                        client.execute_query(query)
                        logger.info(f"✅ Updated {asset}: ${price}")
            except Exception as e:
                logger.error(f"Error in price refresher: {e}")
            finally:
                request_id_ctx.reset(token)
            
            # Sleep for 1 hour
            await asyncio.sleep(3600)
        else:
            # Another worker has the lock, wait and try later
            await asyncio.sleep(300)

@app.on_event("startup")
async def start_refresh_task():
    """Start the background price refresher and market merger on app startup."""
    from app.workers.merger import start_merger_worker
    
    # We use a distributed lock wrapper for merger too
    async def merger_with_lock():
        r = tasks._get_redis()
        while True:
            if not r: 
                await asyncio.sleep(60)
                continue
            
            lock_key = "lock:market_merger"
            if r.set(lock_key, "1", nx=True, ex=1700): # 30 min approx
                logger.info("🛡️ Market Merger Lock Acquired.")
                try:
                    await start_merger_worker()
                except Exception as e:
                    logger.error(f"Merger worker crashed: {e}")
                finally:
                    r.delete(lock_key)
            
            await asyncio.sleep(300)

    asyncio.create_task(asset_price_refresher())
    asyncio.create_task(merger_with_lock())
    
    # --- Pillar 4: Periodic Graph Linting (Every 6 Hours) ---
    async def periodic_linter():
        r = tasks._get_redis()
        while True:
            if not r: 
                await asyncio.sleep(60)
                continue
            
            lock_key = "lock:graph_linter"
            # Try to acquire lock for 6 hours
            if r.set(lock_key, "1", nx=True, ex=21500): 
                logger.info("🧹 Starting Periodic Graph Linting (Scheduled)...")
                try:
                    await linter.run_linting_cycle()
                except Exception as e:
                    logger.error(f"Linter failed: {e}")
            
            await asyncio.sleep(1800) # Check lock every 30 min

    asyncio.create_task(periodic_linter())
