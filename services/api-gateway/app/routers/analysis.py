from fastapi import APIRouter, HTTPException, Query, Body, status
from pydantic import BaseModel
from typing import List, Optional
import httpx
import os
import logging
import time

# Create a logger for this module
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/analysis",
    tags=["analysis"]
)

STRATEGY_CORE_URL = os.getenv("STRATEGY_CORE_URL", "http://strategy-core:8000")

# Request Models
class IndicatorRequest(BaseModel):
    data: List[float]
    params: dict = {}

class RSIRequest(BaseModel):
    close: List[float]
    window: int = 14

class EMAProxyRequest(BaseModel):
    data: List[float]
    span: int = 14

@router.post("/calculate/ema", status_code=200)
async def calculate_ema(req: EMAProxyRequest):
    """
    Proxy EMA calculation to Strategy Core.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Transform to Strategy Core format
            payload = {
                "data": req.data,
                "params": {"span": req.span}
            }
            start_time = time.time()
            response = await client.post(
                f"{STRATEGY_CORE_URL}/calculate/ema",
                json=payload,
                timeout=10.0
            )
            process_time = time.time() - start_time
            logger.info(f"Strategy Core EMA response time: {process_time:.4f}s")
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            
            return response.json()
        except httpx.RequestError as e:
            logger.error(f"Strategy Core unavailable: {str(e)}")
            raise HTTPException(status_code=503, detail=f"Strategy Core unavailable: {str(e)}")
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"EMA Proxy failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")

@router.post("/calculate/rsi", status_code=200)
async def calculate_rsi(req: RSIRequest):
    """
    Proxy RSI calculation to Strategy Core.
    """
    async with httpx.AsyncClient() as client:
        try:
            start_time = time.time()
            response = await client.post(
                f"{STRATEGY_CORE_URL}/calculate/rsi",
                json=req.model_dump(),
                timeout=10.0
            )
            process_time = time.time() - start_time
            logger.info(f"Strategy Core RSI response time: {process_time:.4f}s")
            
            if response.status_code != 200:
                 raise HTTPException(status_code=response.status_code, detail=response.text)
            
            return response.json()
        except httpx.RequestError as e:
            logger.error(f"Strategy Core unavailable: {str(e)}")
            raise HTTPException(status_code=503, detail=f"Strategy Core unavailable: {str(e)}")
        except Exception as e:
            logger.error(f"RSI Proxy failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")
