from fastapi import APIRouter, HTTPException, Request
from typing import Optional
import httpx
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/orchestration",
    tags=["Orchestration"]
)

AI_SERVICE_URL = os.getenv("AI_ANALYST_URL", "http://ai-analyst:8000")

@router.get("/logs")
async def get_orchestration_logs(request: Request, limit: int = 50):
    """Proxy orchestration logs to AI Analyst."""
    request_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": request_id} if request_id else {}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{AI_SERVICE_URL}/api/v1/orchestration/logs?limit={limit}",
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Orchestration logs proxy failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline/status")
async def get_pipeline_status(request: Request):
    """Proxy pipeline status to AI Analyst."""
    request_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": request_id} if request_id else {}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{AI_SERVICE_URL}/api/v1/orchestration/pipeline/status",
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Pipeline status proxy failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
