from fastapi import APIRouter, HTTPException, Depends
import httpx
import os
import logging
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/olympus",
    tags=["Olympus Predictor"]
)

OLYMPUS_URL = os.getenv("OLYMPUS_URL", "http://olympus-predictor:8000")

# Schemas (duplicated for Gateway documentation, or generic proxy)
class PredictionRequest(BaseModel):
    symbol: str = "XAUUSD"
    steps: int = 5

@router.get("/health")
async def health_check():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{OLYMPUS_URL}/health", timeout=2.0)
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Olympus Service Service unreachable: {e}")

@router.post("/predict")
async def predict_gold(req: PredictionRequest):
    """
    Proxy prediction request to Olympus service.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{OLYMPUS_URL}/predict",
                json=req.model_dump(),
                timeout=10.0
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            return resp.json()
        except httpx.RequestError as e:
            logger.error(f"Olympus Connection Failed: {e}")
            raise HTTPException(status_code=503, detail="Olympus Service unreachable")

@router.post("/train")
async def trigger_training():
    """
    Trigger background training task.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{OLYMPUS_URL}/train", timeout=5.0)
            return resp.json()
        except httpx.RequestError as e:
             logger.error(f"Olympus Connection Failed: {e}")
             raise HTTPException(status_code=503, detail="Olympus Service unreachable")
