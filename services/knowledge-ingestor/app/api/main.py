import os
import shutil
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.core.app_config import config
from app.core.logger import get_logger
from app.core.health import StartupGuard
from app.ingestors.hierarchical_ingestor import HierarchicalIngestor
from app.utils.middleware import RequestIDMiddleware
from app.utils.tracing import request_id_ctx

logger = get_logger("OlympusAPI")

app = FastAPI(
    title="Project Olympus Ingestor API",
    description="Professional Knowledge Graph Ingestion Service",
    version="1.0.0"
)
app.add_middleware(RequestIDMiddleware)

# Global Ingestor Instance
ingestor = HierarchicalIngestor()

# Simple In-Memory Task Store (In production, use Redis)
tasks = {}

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
        tasks[task_id]["status"] = "processing"
        logger.info(f"🚀 Background Task {task_id} started for {file_path.name}")
        
        result = await ingestor.run_pipeline(file_path)
        
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = result
        logger.info(f"✅ Background Task {task_id} completed successfully.")
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
        tasks[task_id]["finished_at"] = datetime.now().isoformat()
        logger.error("background_task_failed", extra={"task_id": task_id, "error": str(e)})
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
                tasks[task_id]["status"] = "failed"
                tasks[task_id]["error"] = "Failed to scrape URL or no content found"
                return

            tasks[task_id]["status"] = "ingesting"
            result = await ingestor.run_pipeline_on_text(text, filename=f"web_{task_id}")
            
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["result"] = result
        except Exception as e:
            tasks[task_id]["status"] = "failed"
            tasks[task_id]["error"] = str(e)
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
    return tasks

# --- Background Scheduler for Asset Prices ---
async def asset_price_refresher():
    """Background loop to update top asset prices every hour."""
    from app.tools.market_reader import MarketReaderTool
    from app.tools.falkordb_client import FalkorDBClient
    from app.core.app_config import config
    
    client = FalkorDBClient(host=config.falkor_host, port=config.falkor_port, graph_name=config.graph_name)
    assets = ["Gold", "Bitcoin", "Silver", "Crude Oil", "S&P 500"]
    
    while True:
        # Generate a unique ID for each refresh cycle
        cycle_id = f"refresh-{uuid.uuid4().hex[:8]}"
        token = request_id_ctx.set(cycle_id)
        logger.info("🕒 Starting scheduled asset price refresh...")
        try:
            for asset in assets:
                price = MarketReaderTool.get_spot_price(asset)
                if price:
                    now_str = datetime.now().isoformat()
                    query = f"MERGE (a:Asset {{name: '{asset}'}}) SET a.price = {price}, a.last_updated = '{now_str}'"
                    client.execute_query(query)
                    logger.info(f"✅ Updated {asset}: ${price}")
            
            # Wait for 1 hour (3600 seconds)
            await asyncio.sleep(3600)
        except Exception as e:
            logger.error(f"Error in price refresher: {e}")
            await asyncio.sleep(60) # Retry sooner on error
        finally:
            request_id_ctx.reset(token)

@app.on_event("startup")
async def start_refresh_task():
    """Start the background price refresher and market merger on app startup."""
    from app.workers.merger import start_merger_worker
    asyncio.create_task(asset_price_refresher())
    asyncio.create_task(start_merger_worker())
