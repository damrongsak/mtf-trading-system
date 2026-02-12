from fastapi import APIRouter, HTTPException, Query, Body, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.opportunity_log import OpportunityLog
from pydantic import BaseModel
from app.utils.response import success_response
from typing import List, Optional
import httpx
import os
import logging
import time
from app.repositories.open_interest_repository import OpenInterestRepository

# Create a logger for this module
logger = logging.getLogger(__name__)

router = APIRouter(
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

class SMCRequest(BaseModel):
    open: List[float]
    high: List[float]
    low: List[float]
    close: List[float]
    volume: Optional[List[float]] = None

# ... (imports)
import httpx
from contextlib import asynccontextmanager

# ... (rest of imports)

# Shared HTTP Client
http_client = httpx.AsyncClient(timeout=60.0)

@router.on_event("startup")
async def startup_event():
    global http_client
    http_client = httpx.AsyncClient(timeout=60.0)

@router.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()

@router.post("/calculate/ema", status_code=200)
async def calculate_ema(req: EMAProxyRequest):
    """
    Proxy EMA calculation to Strategy Core.
    """
    try:
        # Transform to Strategy Core format
        payload = {
            "data": req.data,
            "params": {"span": req.span}
        }
        start_time = time.time()
        response = await http_client.post(
            f"{STRATEGY_CORE_URL}/api/v1/calculate/ema",
            json=payload
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
    try:
        start_time = time.time()
        response = await http_client.post(
            f"{STRATEGY_CORE_URL}/api/v1/calculate/rsi",
            json=req.model_dump()
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
    try:
        response = await http_client.post(
            f"{STRATEGY_CORE_URL}/api/v1/calculate/atr",
            json=req.model_dump()
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
    try:
        # MACD in strategy-core app/main.py expects fast, slow, signal
        response = await http_client.post(
            f"{STRATEGY_CORE_URL}/api/v1/calculate/macd",
            json=req.model_dump()
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
    try:
        response = await http_client.post(
            f"{STRATEGY_CORE_URL}/api/v1/calculate/adx",
            json=req.model_dump()
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

@router.post("/calculate/smc", status_code=200)
async def calculate_smc(req: SMCRequest):
    try:
        response = await http_client.post(
            f"{STRATEGY_CORE_URL}/api/v1/calculate/smc",
            json=req.model_dump()
        )
        if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()
    except httpx.RequestError as e:
            logger.error(f"Strategy Core unavailable: {str(e)}")
            raise HTTPException(status_code=503, detail=f"Strategy Core unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"SMC Proxy failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")

@router.get("/opportunities", status_code=200)
def get_opportunities(limit: int = 50, db: Session = Depends(get_db)):
    """
    Get skipped trade opportunities (filtered by Volatility/Sentiment).
    """
    logs = db.query(OpportunityLog).order_by(OpportunityLog.timestamp.desc()).limit(limit).all()
    return logs

DATA_PIPELINE_URL = os.getenv("DATA_PIPELINE_URL", "http://data-pipeline:8000")

@router.get("/positioning/status", status_code=200)
async def get_positioning_status(symbol: str = "XAUUSD", db: Session = Depends(get_db)):
    """
    Aggregated endpoint for MarketStateTool.
    Fetches latest OI snapshot directly from DB and returns analysis with crowding regime.
    """
    try:
        repo = OpenInterestRepository(db)
        
        # 1. Get latest snapshot from DB
        snapshots = repo.get_snapshots(limit=1)
        if not snapshots:
            # Silently return empty if no snapshots available
            return success_response(data={
                "symbol": symbol,
                "pcr": 1.0,
                "crowding_regime": "Balanced",
                "max_pain": 0.0,
                "oi_skew_pct": 0.0,
                "regime": "Neutral"
            })
            
        snapshot_at = snapshots[0].snapshot_at

        # 2. Get Analysis from Repo
        analysis = repo.get_analysis_data(snapshot_at=snapshot_at)
        summary = analysis.get("summary", {})
        pcr = summary.get("pcr", 1.0)

        # 3. Derive Crowding Regime
        regime = "Balanced"
        if pcr > 1.5:
            regime = "Short Crowded"
        elif pcr < 0.7:
            regime = "Long Crowded"

        # 4. Map to Tool expectations
        return success_response(data={
            "symbol": symbol,
            "pcr": pcr,
            "crowding_regime": regime,
            "max_pain": summary.get("max_call_strike", 0.0),
            "oi_skew_pct": 0.0, 
            "regime": regime,
            "snapshot_at": snapshot_at
        })


    except Exception as e:
        logger.error(f"Positioning aggregate failed: {e}")
        return success_response(data={
            "symbol": symbol,
            "error": str(e),
            "pcr": 1.0,
            "crowding_regime": "Unavailable"
        })

@router.get("/market-regime/{symbol}", status_code=200)
async def get_market_regime(symbol: str, timeframe: str = "H1", bias: str = "NEUTRAL"):
    """
    Fetches Adaptive Guardrails (Regime, Fakeout, Risk) from Strategy Core.
    """
    try:
        payload = {
            "symbol": symbol,
            "timeframe": timeframe,
            "bias": bias
        }
        
        # Call Strategy Core
        # Note: Strategy Core endpoint is POST /api/v1/market/regime
        url = f"{STRATEGY_CORE_URL}/api/v1/market/regime"
        
        response = await http_client.post(url, json=payload)
        
        if response.status_code != 200:
             logger.error(f"Strategy Core Regime Check failed: {response.text}")
             # Return fallback or error?
             raise HTTPException(status_code=response.status_code, detail=response.text)
             
        data = response.json()
        return success_response(data=data)
        
    except httpx.RequestError as e:
        logger.error(f"Strategy Core unavailable: {str(e)}")
        raise HTTPException(status_code=503, detail="Strategy Core unavailable")
    except Exception as e:
        logger.error(f"Market Regime Proxy failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
