from fastapi import APIRouter, HTTPException, Query, Body, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import get_current_user
from app.models.user import User
from app.utils.fund_resolver import get_best_fund_for_user

from app.models.opportunity_log import OpportunityLog
from pydantic import BaseModel
from app.utils.response import success_response
from app.schemas.open_interest import UnifiedOIProfileResponse
from app.schemas.opportunity import OpportunityLogResponse
from typing import List, Optional, Dict, Any
import httpx
from datetime import datetime
import os
import logging
import time
import json
import redis.asyncio as redis
from app.repositories.open_interest_repository import OpenInterestRepository
import traceback
from app.schemas.smc import (
    SMCChecklistItem,
    SMCVisuals,
    SMCDebugInfo,
    SMCAnalysisResponse,
    SMCAnalysisRequest
)

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

# SMC Schemas moved to app/schemas/smc.py

class QuantAnalyzeRequest(BaseModel):
    symbol: str
    timeframe: str = "H1"
    limit: int = 1000
    fund_id: Optional[str] = None

class QuantSizingRequest(BaseModel):
    symbol: str
    entry_price: float
    stop_loss: float
    equity: float
    strategy_id: Optional[str] = None
    timeframe: str = "H1"
    limit: int = 1000
    fund_id: Optional[str] = None

class RegimeRequest(BaseModel):
    symbol: str
    timeframe: str = "H1"
    bias: str = "NEUTRAL"
    fund_id: Optional[str] = None

class PIVVolatilityRequest(BaseModel):
    symbol: str
    timeframe: str = "H1"
    fund_id: Optional[str] = None

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

@router.post("/smc", status_code=200, response_model=SMCAnalysisResponse)
async def analyze_smc_institutional(
    req: SMCAnalysisRequest, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Advanced Institutional SMC Analysis (Multi-Timeframe).
    Includes Confluence Scoring (1-6) and Case B Mitigation detection.
    """
    try:
        from app.utils.symbol_utils import normalize_symbol
        from app.models.user_fund import UserFund
        
        # 1. Normalize Symbol (Logic-First Standard)
        req.symbol = normalize_symbol(req.symbol)
        
        # 2. Inject Primary Fund ID if not provided
        if not req.fund_id:
            user_fund = db.query(UserFund).filter(UserFund.user_id == current_user.id).first()
            if user_fund:
                req.fund_id = str(user_fund.fund_id)
        
        start_time = time.time()
        response = await http_client.post(
            f"{STRATEGY_CORE_URL}/api/v1/calculate/smc/mtf",
            json=req.model_dump()
        )
        process_time = time.time() - start_time
        logger.info(f"Strategy Core SMC MTF response time: {process_time:.4f}s for {req.symbol} (Fund: {req.fund_id})")
        
        if response.status_code != 200:
                logger.error(f"Strategy Core returned {response.status_code}: {response.text}")
                raise HTTPException(status_code=response.status_code, detail=response.text)
        
        data = response.json()
        return SMCAnalysisResponse(**data)
    except httpx.RequestError as e:
        logger.error(f"Strategy Core connection error: {str(e)}")
        raise HTTPException(status_code=503, detail="Strategy Core unavailable")
    except Exception as e:
        logger.error(f"SMC MTF Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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

@router.post("/market_regime", status_code=200)
async def post_market_regime(
    req: RegimeRequest, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Proxy Adaptive Guardrails (Regime, Fakeout, Risk) to Strategy Core via POST.
    """
    try:
        payload = req.model_dump()
        
        # 1. Resolve Fund ID (Institutional Data Isolation)
        if not payload.get("fund_id"):
            fund_id = get_best_fund_for_user(db, current_user.id)
            if fund_id:
                payload["fund_id"] = fund_id
        
        # 2. Call Strategy Core
        url = f"{STRATEGY_CORE_URL}/api/v1/market/regime"
        headers = {"X-User-Id": str(current_user.id)}
        
        response = await http_client.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
             logger.error(f"Strategy Core Regime Check failed: {response.text}")
             raise HTTPException(status_code=response.status_code, detail=response.text)
             
        data = response.json()
        return success_response(data=data)
        
    except httpx.RequestError as e:
        logger.error(f"Strategy Core unavailable: {str(e)}")
        raise HTTPException(status_code=503, detail="Strategy Core unavailable")
    except Exception as e:
        logger.error(f"Market Regime Proxy failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/piv_volatility", status_code=200)
async def post_piv_volatility(
    req: PIVVolatilityRequest, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Proxy PIV Volatility (Statistical Probability Bands) to Strategy Core.
    """
    try:
        payload = req.model_dump()
        
        # 1. Resolve Fund ID (Institutional Data Isolation)
        if not payload.get("fund_id"):
            fund_id = get_best_fund_for_user(db, current_user.id)
            if fund_id:
                payload["fund_id"] = fund_id
        
        # 2. Call Strategy Core
        url = f"{STRATEGY_CORE_URL}/api/v1/market/volatility/piv"
        headers = {"X-User-Id": str(current_user.id)}
        
        response = await http_client.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
             logger.error(f"Strategy Core Volatility Check failed: {response.text}")
             raise HTTPException(status_code=response.status_code, detail=response.text)
             
        data = response.json()
        return success_response(data=data)
        
    except httpx.RequestError as e:
        logger.error(f"Strategy Core unavailable: {str(e)}")
        raise HTTPException(status_code=503, detail="Strategy Core unavailable")
    except Exception as e:
        logger.error(f"PIV Volatility Proxy failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gamma/levels", status_code=200)
async def get_gamma_levels(
    symbol: str = "XAUUSD", 
    current_price: Optional[float] = None,
    max_dte: Optional[int] = None,
    snapshot_at: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetches Gamma Levels and Market Regime from Strategy Core.
    """
    try:
        headers = {"X-User-ID": str(current_user.id)}
        
        # Resolve Fund ID (Institutional Data Isolation)
        fund_id = get_best_fund_for_user(db, current_user.id)
        
        url = f"{STRATEGY_CORE_URL}/api/v1/analysis/gamma/levels"
        params = {"symbol": symbol}
        if fund_id:
            params["fund_id"] = fund_id
        if current_price:
            params["current_price"] = str(current_price)
        if max_dte:
            params["max_dte"] = str(max_dte)
        if snapshot_at:
            params["snapshot_at"] = snapshot_at
            
        response = await http_client.get(url, params=params, headers=headers)
        
        if response.status_code != 200:
             if response.status_code == 404:
                 return success_response(data={"error": "No Gamma Data Found"})
             raise HTTPException(status_code=response.status_code, detail=response.text)
             
        data = response.json()
        return success_response(data=data)
        
    except httpx.RequestError as e:
        logger.error(f"Strategy Core unavailable: {str(e)}")
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
async def proxy_quant_analyze(
    req: QuantAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Proxy Quant Map analysis to Strategy Core.
    """
    try:
        # Resolve Fund ID if missing (Institutional Data Isolation)
        payload = req.model_dump()
        if not payload.get("fund_id"):
            fund_id = get_best_fund_for_user(db, current_user.id)
            if fund_id:
                payload["fund_id"] = fund_id
            else:
                logger.warning(f"Could not resolve fund_id for user {current_user.id}")

        headers = {"X-User-Id": str(current_user.id)}
        logger.info(f"Proxying Quant Analyze: {payload}")
        response = await http_client.post(
            f"{STRATEGY_CORE_URL}/api/v1/quant/analyze",
            json=payload,
            headers=headers
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

@router.post("/quant/sizing", status_code=200)
async def proxy_quant_sizing(
    req: QuantSizingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Proxy Quant Positioning/Sizing to Strategy Core.
    """
    try:
        # Resolve Fund ID if missing (Institutional Data Isolation)
        payload = req.model_dump()
        if not payload.get("fund_id"):
            fund_id = get_best_fund_for_user(db, current_user.id)
            if fund_id:
                payload["fund_id"] = fund_id
                logger.info(f"Resolved fund_id for sizing: {fund_id}")
            else:
                logger.warning(f"Could not resolve fund_id for sizing: user {current_user.id}")

        headers = {"X-User-Id": str(current_user.id)}
        logger.info(f"Proxying Quant Sizing: {payload}")
        response = await http_client.post(
            f"{STRATEGY_CORE_URL}/api/v1/quant/size",
            json=payload,
            headers=headers
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
from app.models.trade import Trade, TradeStatus
from sqlalchemy import func, extract, desc

@router.get("/metrics/edge-optimization", status_code=200)
async def get_edge_optimization(
    fund_id: Optional[str] = Query(None),
    strategy_name: Optional[str] = Query(None),
    lookback_days: int = Query(30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns a statistical matrix of PnL grouped by Entry Hour and Day of Week.
    Identifies the 'Window of Edge' for institutional allocation.
    """
    try:
        # 1. Base Query: Only Closed Trades for current user
        query = db.query(extract('hour', Trade.signal_timestamp).label('hour'), extract('dow', Trade.signal_timestamp).label('dow'), func.sum(Trade.pnl_usd).label('total_pnl'), func.count(Trade.trade_id).label('trade_count'), func.avg(Trade.pnl_usd).label('avg_pnl')).filter(Trade.status == TradeStatus.CLOSED).filter(Trade.user_id == current_user.id)

        # 2. Apply Filters
        if fund_id:
            query = query.filter(Trade.fund_id == fund_id)
        if strategy_name:
            query = query.filter(Trade.strategy_name == strategy_name)
        
        # Lookback filter
        if lookback_days > 0:
            from datetime import datetime, timedelta, timezone
            since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            query = query.filter(Trade.signal_timestamp >= since)

        # 3. Group and Execute
        results = query.group_by('hour', 'dow').all()

        # 4. Format into Matrix
        # Matrix structure: {hour: {dow: pnl}}
        matrix = {}
        total_pnl = 0.0
        best_pnl = -float('inf')
        best_hour = -1
        best_day = -1

        for r in results:
            h = int(r.hour)
            d = int(r.dow)
            pnl = float(r.total_pnl or 0.0)
            
            if h not in matrix:
                matrix[h] = {}
            matrix[h][d] = pnl
            
            total_pnl += pnl
            if pnl > best_pnl:
                best_pnl = pnl
                best_hour = h
                best_day = d

        return success_response(data={
            "matrix": matrix,
            "summary": {
                "best_hour": best_hour,
                "best_day": best_day,
                "best_pnl": best_pnl if best_pnl != -float('inf') else 0.0,
                "total_pnl": total_pnl,
                "trade_count": sum(int(r.trade_count) for r in results)
            }
        })

    except Exception as e:
        logger.error(f"Edge Optimization analysis failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
