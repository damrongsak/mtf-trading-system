import os
import httpx
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, BackgroundTasks, Body
from app.utils.http_client import get_internal_client
from app.utils.response import success_response
from app.schemas.response import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/knowledge",
    tags=["knowledge"]
)

KNOWLEDGE_SERVICE_URL = os.getenv("KNOWLEDGE_INGESTOR_URL", "http://knowledge-ingestor:8000")

@router.delete("/graph")
async def delete_graph(request: Request):
    """Proxy graph deletion request to Knowledge Ingestor."""
    request_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": request_id} if request_id else {}
    
    async with await get_internal_client() as client:
        try:
            response = await client.delete(
                f"{KNOWLEDGE_SERVICE_URL}/graph",
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except Exception as e:
            raise HTTPException(status_code=503, detail="Knowledge Ingestor service unreachable")

@router.post("/ingest", status_code=202)
async def ingest_file(request: Request, file: UploadFile = File(...)):
    """Proxy file upload to Knowledge Ingestor."""
    request_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": request_id} if request_id else {}
    
    async with await get_internal_client() as client:
        try:
            # Forward the file
            files = {"file": (file.filename, file.file, file.content_type)}
            response = await client.post(
                f"{KNOWLEDGE_SERVICE_URL}/ingest",
                files=files,
                headers=headers,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(f"Knowledge service error {exc.response.status_code}: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except Exception as e:
            logger.error(f"Knowledge service connection failed: {e}")
            raise HTTPException(status_code=503, detail="Knowledge Ingestor service unreachable")

@router.post("/ingest/batch", status_code=202)
async def ingest_batch(request: Request, files: List[UploadFile] = File(...)):
    """Proxy batch file upload to Knowledge Ingestor."""
    request_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": request_id} if request_id else {}
    
    async with await get_internal_client() as client:
        try:
            forward_files = [("files", (f.filename, f.file, f.content_type)) for f in files]
            response = await client.post(
                f"{KNOWLEDGE_SERVICE_URL}/ingest/batch",
                files=forward_files,
                headers=headers,
                timeout=120.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except Exception as e:
            raise HTTPException(status_code=503, detail="Knowledge Ingestor service unreachable")

@router.post("/ingest/url", status_code=202)
async def ingest_url(request: Request, payload: Dict[str, Any] = Body(...)):
    """Proxy URL ingestion to Knowledge Ingestor."""
    request_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": request_id} if request_id else {}
    
    async with await get_internal_client() as client:
        try:
            response = await client.post(
                f"{KNOWLEDGE_SERVICE_URL}/ingest/url",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except Exception as e:
            raise HTTPException(status_code=503, detail="Knowledge Ingestor service unreachable")

@router.post("/ingest/directory", status_code=202)
async def ingest_directory(request: Request, payload: Dict[str, Any] = Body(...)):
    """Proxy directory ingestion request to Knowledge Ingestor."""
    request_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": request_id} if request_id else {}
    
    async with await get_internal_client() as client:
        try:
            response = await client.post(
                f"{KNOWLEDGE_SERVICE_URL}/ingest/directory",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except Exception as e:
            raise HTTPException(status_code=503, detail="Knowledge Ingestor service unreachable")

@router.get("/status/{task_id}")
async def get_task_status(task_id: str, request: Request):
    """Proxy task status check to Knowledge Ingestor."""
    request_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": request_id} if request_id else {}
    
    async with await get_internal_client() as client:
        try:
            response = await client.get(
                f"{KNOWLEDGE_SERVICE_URL}/status/{task_id}",
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except Exception as e:
            raise HTTPException(status_code=503, detail="Knowledge Ingestor service unreachable")

@router.get("/tasks")
async def list_tasks(request: Request):
    """Proxy task list request to Knowledge Ingestor."""
    request_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": request_id} if request_id else {}
    
    async with await get_internal_client() as client:
        try:
            response = await client.get(
                f"{KNOWLEDGE_SERVICE_URL}/tasks",
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except Exception as e:
            raise HTTPException(status_code=503, detail="Knowledge Ingestor service unreachable")
