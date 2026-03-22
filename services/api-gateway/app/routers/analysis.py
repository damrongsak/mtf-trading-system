from fastapi import APIRouter, HTTPException, Query, Body, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.opportunity_log import OpportunityLog
from pydantic import BaseModel
from app.utils.response import success_response
from app.schemas.open_interest import UnifiedOIProfileResponse
from app.schemas.opportunity import OpportunityLogResponse
from typing import List, Optional
import httpx
import os
import logging
import time
import json
import redis.asyncio as redis
from app.repositories.open_interest_repository import OpenInterestRepository
import traceback

# Create a logger for this module
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

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
    symbol: str
    timeframe: str = "H1"
    open: List[float]
    high: List[float]
    low: List[float]
    close: List[float]
    volume: Optional[List[float]] = None
    timestamps: Optional[List[str]] = None
    oi_call: Optional[List[float]] = None
    oi_put: Optional[List[float]] = None
    oi_strikes: Optional[List[float]] = None

class QuantAnalyzeRequest(BaseModel):
    symbol: str
    timeframe: str = "H1"
    limit: int = 1000

class QuantSizingRequest(BaseModel):
    symbol: str
    entry_price: float
    stop_loss: float
    equity: float
    strategy_id: Optional[str] = None
    timeframe: str = "H1"
    limit: int = 1000

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

@router.get("/opportunities", status_code=200, response_model=List[OpportunityLogResponse])
def get_opportunities(limit: int = 50, db: Session = Depends(get_db)):
    """
    Get skipped trade opportunities (filtered by Volatility/Sentiment).
    """
    try:
        logs = db.query(OpportunityLog).order_by(OpportunityLog.timestamp.desc()).limit(limit).all()
        return logs
    except Exception as e:
        logger.error(f"Failed to fetch opportunity logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch opportunity logs: {str(e)}")

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
        logger.error(f"Market Regime Proxy failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gamma/levels", status_code=200)
async def get_gamma_levels(symbol: str = "XAUUSD", current_price: Optional[float] = None):
    """
    Fetches Gamma Levels and Market Regime from Strategy Core.
    """
    try:
        url = f"{STRATEGY_CORE_URL}/api/v1/analysis/gamma/levels"
        params = {"symbol": symbol}
        if current_price:
            params["current_price"] = str(current_price)
            
        response = await http_client.get(url, params=params)
        
        if response.status_code != 200:
             # If 404/500, might be no data or service down.
             # Return empty/error structure rather than failing hard if possible?
             # But here we proxy, so maybe just pass through error or return standard structure
             if response.status_code == 404:
                 return success_response(data={"error": "No Gamma Data Found"})
             raise HTTPException(status_code=response.status_code, detail=response.text)
             
        data = response.json()
        return success_response(data=data)
        
    except httpx.RequestError as e:
        logger.error(f"Strategy Core unavailable: {str(e)}")
        # Start of fallback for AI tool
        return success_response(data={"error": "Service Unavailable"})
    except Exception as e:
        logger.error(f"Gamma Levels Proxy failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/oi/unified-profile", status_code=200)
async def get_unified_oi_profile(
    symbol: str = "XAUUSD",
    db: Session = Depends(get_db)
):
    """
    Unified Endpoint for Gold OI Dashboard.
    Combines: Sentiment (PCR), Gamma Levels (Walls), and Session Drift.
    """
    try:
        repo = OpenInterestRepository(db)
        
        # 1. Get latest 2 snapshots
        snapshots = repo.get_snapshots(limit=2)
        if len(snapshots) < 1:
            raise HTTPException(status_code=404, detail="No OI data snapshots found")
            
        latest_ts = snapshots[0].snapshot_at
        prev_ts = snapshots[1].snapshot_at if len(snapshots) > 1 else None
        
        # 2. Proxy Gamma Levels from Strategy Core (contains confluence & regimes)
        gamma_url = f"{STRATEGY_CORE_URL}/api/v1/analysis/gamma/levels"
        gamma_resp = await http_client.get(gamma_url, params={"symbol": symbol})
        
        gamma_data = {}
        if gamma_resp.status_code == 200:
            gamma_data = gamma_resp.json()
        
        # 3. Calculate Drift Analysis (latest vs previous)
        latest_analysis = repo.get_analysis_data(latest_ts)
        pcr = latest_analysis.get("summary", {}).get("pcr", 1.0)
        
        # Determine Crowding Regime
        crowding_regime = "Balanced"
        if pcr > 1.5:
            crowding_regime = "Short Crowded"
        elif pcr < 0.7:
            crowding_regime = "Long Crowded"

        drift = {
            "pcr_drift": 0.0,
            "net_oi_drift": 0,
            "call_wall_shift": 0.0,
            "put_wall_shift": 0.0,
            "oiwap_shift": 0.0,
            "sentiment": "Neutral",
            "latest_summary": latest_analysis.get("summary", {}),
            "prev_summary": {}
        }
        
        if prev_ts:
            drift = repo.get_drift_analysis(latest_ts, prev_ts)

        # 4. Final Aggregation
        profile = {
            "symbol": symbol,
            "snapshot_at": latest_ts,
            "prev_snapshot_at": prev_ts,
            "price": gamma_data.get("underlying_price", 0.0),
            "gamma_regime": gamma_data.get("regime", {}).get("regime", "UNKNOWN"),
            "crowding_regime": crowding_regime,
            "sentiment_drift": drift,
            "gamma_levels": gamma_data.get("levels", []),
            "summary": latest_analysis.get("summary", {})
        }

        return success_response(data=profile)

    except Exception as e:
        logger.error(f"Unified OI Profile failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to aggregate OI profile: {str(e)}")

@router.post("/quant/analyze", status_code=200)
async def proxy_quant_analyze(req: QuantAnalyzeRequest):
    """
    Proxy Quant Map analysis to Strategy Core.
    """
    try:
        response = await http_client.post(
            f"{STRATEGY_CORE_URL}/api/v1/quant/analyze",
            json=req.model_dump()
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return success_response(data=response.json())
    except httpx.RequestError as e:
        logger.error(f"Strategy Core unavailable: {str(e)}")
        raise HTTPException(status_code=503, detail="Strategy Core unavailable")
    except Exception as e:
        logger.error(f"Quant Analyze Proxy failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quant/size", status_code=200)
async def proxy_quant_sizing(req: QuantSizingRequest):
    """
    Proxy Quant Positioning/Sizing to Strategy Core.
    """
    try:
        response = await http_client.post(
            f"{STRATEGY_CORE_URL}/api/v1/quant/size",
            json=req.model_dump()
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return success_response(data=response.json())
    except httpx.RequestError as e:
        logger.error(f"Strategy Core unavailable: {str(e)}")
        raise HTTPException(status_code=503, detail="Strategy Core unavailable")
    except Exception as e:
        logger.error(f"Quant Sizing Proxy failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sentiment/cached", status_code=200)
async def get_cached_sentiment(symbol: str = "XAUUSD"):
    """
    Fetches the sub-millisecond AI sentiment score and reason from Redis.
    """
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        cached_data = await r.get(f"sentiment:{symbol}")
        await r.aclose()
        
        if cached_data:
            sentiment_data = json.loads(cached_data)
        else:
            sentiment_data = {"score": 0.0, "reason": "No cached sentiment"}
            
        return success_response(data={
            "symbol": symbol,
            "sentiment": sentiment_data
        })
    except Exception as e:
        logger.error(f"Failed to fetch cached sentiment: {e}")
        return success_response(data={
            "symbol": symbol,
            "sentiment": {"score": 0.0, "reason": "Error fetching sentiment"}
        })

@router.get("/macro/status", status_code=200)
async def get_macro_status():
    """
    Fetches real-time macro indicators (DXY, VIX, GVZ) from Redis.
    """
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        labels = ["dxy", "vix", "gvz"]
        results = {}
        
        for label in labels:
            # Fetch rich JSON data if available
            raw_json = await r.get(f"market_data:{label}")
            if raw_json:
                results[label] = json.loads(raw_json)
            else:
                # Fallback to simple value
                val = await r.get(f"macro:{label}")
                results[label] = {"value": float(val) if val else 0.0, "status": "legacy"}
        
        await r.aclose()
        return success_response(data=results)
    except Exception as e:
        logger.error(f"Failed to fetch macro status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
