from fastapi import APIRouter, HTTPException, Query, Body, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.opportunity_log import OpportunityLog
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

class ATRRequest(BaseModel):
    high: List[float]
    low: List[float]
    close: List[float]
    window: int = 14

class MACDRequest(BaseModel):
    close: List[float]
    fast: int = 12
    slow: int = 26
    signal: int = 9

class ADXRequest(BaseModel):
    high: List[float]
    low: List[float]
    close: List[float]
    length: int = 14

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
                f"{STRATEGY_CORE_URL}/api/v1/calculate/ema",
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
                f"{STRATEGY_CORE_URL}/api/v1/calculate/rsi",
                json=req.model_dump(),
                timeout=10.0
            )
            process_time = time.time() - start_time
            logger.info(f"Strategy Core RSI response time: {process_time:.4f}s")
            
            if response.status_code != 200:
                 logger.error(f"Strategy Core returned {response.status_code}: {response.text}")
                 raise HTTPException(status_code=response.status_code, detail=response.text)
            
            return response.json()
        except httpx.RequestError as e:
            logger.error(f"Strategy Core connection error for {e.request.url}: {type(e).__name__} - {str(e)}")
            raise HTTPException(status_code=503, detail=f"Strategy Core unavailable: {type(e).__name__} - {str(e)}")
        except Exception as e:
            logger.error(f"RSI Proxy failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")

@router.post("/calculate/atr", status_code=200)
async def calculate_atr(req: ATRRequest):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{STRATEGY_CORE_URL}/api/v1/calculate/atr",
                json=req.model_dump(),
                timeout=30.0
            )
            if response.status_code != 200:
                 logger.error(f"Strategy Core returned {response.status_code}: {response.text}")
                 raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
        except httpx.RequestError as e:
             logger.error(f"Strategy Core connection error for {e.request.url}: {type(e).__name__} - {str(e)}")
             raise HTTPException(status_code=503, detail=f"Strategy Core unavailable: {type(e).__name__} - {str(e)}")
        except Exception as e:
            logger.error(f"ATR Proxy failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")

@router.post("/calculate/macd", status_code=200)
async def calculate_macd(req: MACDRequest):
    async with httpx.AsyncClient() as client:
        try:
            # MACD in strategy-core app/main.py expects fast, slow, signal
            response = await client.post(
                f"{STRATEGY_CORE_URL}/api/v1/calculate/macd",
                json=req.model_dump(),
                timeout=10.0
            )
            if response.status_code != 200:
                 raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
        except httpx.RequestError as e:
             logger.error(f"Strategy Core unavailable: {str(e)}")
             raise HTTPException(status_code=503, detail=f"Strategy Core unavailable: {str(e)}")
        except Exception as e:
            logger.error(f"MACD Proxy failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")

@router.post("/calculate/adx", status_code=200)
async def calculate_adx(req: ADXRequest):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{STRATEGY_CORE_URL}/api/v1/calculate/adx",
                json=req.model_dump(),
                timeout=10.0
            )
            if response.status_code != 200:
                 raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
        except httpx.RequestError as e:
             logger.error(f"Strategy Core unavailable: {str(e)}")
             raise HTTPException(status_code=503, detail=f"Strategy Core unavailable: {str(e)}")
        except Exception as e:
            logger.error(f"ADX Proxy failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")

@router.get("/opportunities", status_code=200)
def get_opportunities(limit: int = 50, db: Session = Depends(get_db)):
    """
    Get skipped trade opportunities (filtered by Volatility/Sentiment).
    """
    logs = db.query(OpportunityLog).order_by(OpportunityLog.timestamp.desc()).limit(limit).all()
    return logs
