from fastapi import APIRouter, UploadFile, File, Query, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import get_current_user
from app.repositories.open_interest_repository import OpenInterestRepository
from app.schemas.open_interest import (
    OpenInterestSnapshotResponse,
    OpenInterestRecordResponse,
    OpenInterestAnalysisResponse
)
from app.utils.redis_client import redis_client
from app.utils.http_client import get_internal_client
from app.schemas.response import APIResponse
from app.utils.response import success_response, error_response
import httpx
import json
from typing import Optional, List
from datetime import datetime
import os
import logging
import traceback

router = APIRouter(
    prefix="/api/v1/data",
    tags=["data"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

DATA_SERVICE_URL = os.getenv("DATA_PIPELINE_URL", "http://data-pipeline:8000")

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_historical_data(
    file: UploadFile = File(...),
    symbol: str = Query(..., description="Symbol (e.g., XAUUSD)"),
    timeframe: str = Query(..., description="Timeframe (e.g., 15m)")
):
    """
    Upload historical OHLCV data via CSV.
    Proxies the request to the Data Pipeline service.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV.")

    async with await get_internal_client() as client:
        try:
            # Read file content
            content = await file.read()
            
            # Prepare multipart upload
            files = {
                'file': (file.filename, content, file.content_type or 'text/csv')
            }
            params = {
                'symbol': symbol,
                'timeframe': timeframe
            }
            
            # Forward to Data Pipeline
            # Note: Internal service path is /api/v1/upload
            response = await client.post(
                f"{DATA_SERVICE_URL}/api/v1/upload",
                params=params,
                files=files,
                timeout=300.0 # Allow more time for large uploads
            )
            
            if response.status_code != 201:
                # Propagate error details
                try:
                    error_detail = response.json().get('detail', response.text)
                except:
                    error_detail = response.text
                raise HTTPException(status_code=response.status_code, detail=error_detail)
            
            return response.json()

        except httpx.RequestError as e:
            logger.error(f"Data Service unavailable (Historical Upload): {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=503, detail=f"Data Service unavailable: {str(e)}")
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Historical Upload failed: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/open-interest/upload", status_code=status.HTTP_201_CREATED)
async def upload_open_interest(
    file: UploadFile = File(...),
    snapshot_at: Optional[datetime] = None
):
    """
    Upload Open Interest Matrix Excel file.
    Proxies to Data Pipeline.
    """
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx).")

    async with await get_internal_client() as client:
        try:
            content = await file.read()
            files = {'file': (file.filename, content, file.content_type or 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            params = {}
            if snapshot_at:
                params['snapshot_at'] = snapshot_at.isoformat()

            response = await client.post(
                f"{DATA_SERVICE_URL}/api/v1/ingest/open-interest",
                params=params,
                files=files,
                timeout=300.0
            )
            if response.status_code != 201:
                try:
                    err = response.json()
                    detail = err.get('detail', response.text)
                except:
                    detail = response.text
                logger.error(f"Data Pipeline Error (OI Upload): {response.status_code} - {detail}")
                raise HTTPException(status_code=response.status_code, detail=detail)

            return success_response(data=response.json())

        except httpx.RequestError as e:
            logger.error(f"Data Service unavailable (OI Upload): {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=503, detail=f"Data Service unavailable: {type(e).__name__} - {str(e)}")
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"OI Upload failed: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

@router.get("/open-interest/snapshots", response_model=APIResponse[List[OpenInterestSnapshotResponse]])
async def get_open_interest_snapshots(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get available OI snapshots. Cached in Redis (ECST Pattern).
    """
    cache_key = f"oi:snapshots:{limit}"
    
    try:
        r = await redis_client.get_client()
        cached = await r.get(cache_key)
        if cached:
            logger.info("OI Snapshots: Cache HIT")
            return success_response(data=json.loads(cached))
    except Exception as re:
        logger.warning(f"Redis cache check failed: {re}")

    try:
        repo = OpenInterestRepository(db)
        results = repo.get_snapshots(limit)
        
        data = [
            {
                "snapshot_at": r.snapshot_at.isoformat(),
                "count": r.count,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in results
        ]
        
        # Update Cache
        try:
            r = await redis_client.get_client()
            await r.setex(cache_key, 300, json.dumps(data, default=str)) # 5 min TTL
            logger.info("OI Snapshots: Cache UPDATED")
        except Exception as re:
            logger.warning(f"Redis cache update failed: {re}")
            
        return success_response(data=data)
    except Exception as e:
        logger.error(f"Fetch snapshots failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")

@router.get("/open-interest/details", response_model=APIResponse[List[OpenInterestRecordResponse]])
async def get_open_interest_details(
    snapshot_at: datetime = Query(...),
    contract: Optional[str] = Query(None),
    min_oi: int = Query(2000),
    max_oi: Optional[int] = Query(5500),
    smart_filter: bool = Query(True),
    db: Session = Depends(get_db)
):
    """
    Get detailed OI records directly from DB.
    """
    try:
        repo = OpenInterestRepository(db)
        results = repo.get_by_snapshot(
            snapshot_at=snapshot_at,
            contract_symbol=contract,
            min_oi=min_oi,
            max_oi=max_oi,
            smart_filter=smart_filter
        )
        
        return success_response(data=[OpenInterestRecordResponse.model_validate(r) for r in results])
    except Exception as e:
        logger.error(f"Fetch details failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")

@router.get("/open-interest/analysis", response_model=APIResponse[OpenInterestAnalysisResponse])
async def get_open_interest_analysis(
    snapshot_at: datetime = Query(...),
    contract: Optional[str] = Query(None),
    min_oi: int = Query(0),
    max_oi: Optional[int] = Query(None),
    min_dte: Optional[int] = Query(None),
    max_dte: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get detailed OI analysis directly from DB. Cached in Redis (5 min).
    """
    cache_key = f"oi:analysis:{snapshot_at.isoformat()}:{contract}:{min_oi}:{max_oi}:{min_dte}:{max_dte}"
    
    try:
        r = await redis_client.get_client()
        cached = await r.get(cache_key)
        if cached:
            logger.info("OI Analysis: Cache HIT")
            return success_response(data=json.loads(cached))
    except Exception as re:
        logger.warning(f"Redis cache check failed: {re}")

    try:
        repo = OpenInterestRepository(db)
        data = repo.get_analysis_data(
            snapshot_at=snapshot_at,
            contract_symbol=contract,
            min_oi=min_oi,
            max_oi=max_oi,
            min_dte=min_dte,
            max_dte=max_dte
        )
        
        # Update Cache
        try:
            r = await redis_client.get_client()
            await r.setex(cache_key, 300, json.dumps(data, default=str))
            logger.info("OI Analysis: Cache UPDATED")
        except Exception as re:
            logger.warning(f"Redis cache update failed: {re}")

        return success_response(data=data)
    except Exception as e:
        logger.error(f"Fetch analysis failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")

@router.get("/open-interest/contracts", response_model=APIResponse[List[str]])
async def get_open_interest_contracts(
    snapshot_at: datetime = Query(...),
    db: Session = Depends(get_db)
):
    """
    Get list of contracts directly from DB.
    """
    try:
        repo = OpenInterestRepository(db)
        contracts = repo.get_available_contracts(snapshot_at)
        return success_response(data=contracts)
    except Exception as e:
        logger.error(f"Fetch contracts failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")

@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(
    symbol: str = Query(..., description="Symbol to sync (e.g. XAU_USD)")
):
    """
    Trigger manual data sync for a symbol.
    Proxies to Data Pipeline.
    """
    async with await get_internal_client() as client:
        try:
            response = await client.post(
                f"{DATA_SERVICE_URL}/api/v1/ingest/manual",
                params={"symbol": symbol},
                timeout=10.0
            )
            
            if response.status_code not in [200, 202]:
                 logger.error(f"Failed to trigger sync: {response.status_code} - {response.text}")
                 raise HTTPException(status_code=response.status_code, detail=response.text)
            
            return success_response(data=response.json())
            
        except Exception as e:
            logger.error(f"Manual sync failed: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@router.get("/candles")
async def get_candles(
    symbol: str = Query(..., description="Symbol (e.g., XAUUSD)"),
    timeframe: str = Query(..., description="Timeframe (e.g., 15m)"),
    broker: str = Query("CTRADER", description="Data Provider (e.g. OANDA, BINANCE, CTRADER)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000)
):
    """
    Get candles from Data Pipeline. Proxy endpoint.
    """
    async with await get_internal_client() as client:
        try:
            # Normalize and validate symbol
            clean_symbol = symbol.strip().upper()
            if '{' in clean_symbol or '}' in clean_symbol:
                logger.warning(f"Malformed symbol detected in request: {symbol}")
                raise HTTPException(status_code=400, detail="Invalid symbol format")

            params = {
                "symbol": clean_symbol,
                "timeframe": timeframe,
                "broker": broker,
                "page": page,
                "page_size": page_size
            }
            response = await client.get(
                f"{DATA_SERVICE_URL}/api/v1/candles",
                params=params,
                timeout=10.0
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch candles: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
            return success_response(data=response.json())
            
        except Exception as e:
            logger.error(f"Fetch candles failed: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")

@router.get("/symbols")
async def get_active_symbols(
    broker: str = Query("CTRADER", description="Filter by broker name")
):
    """
    Get list of active symbols for a specific broker.
    Proxies to Data Pipeline.
    """
    async with await get_internal_client() as client:
        try:
            response = await client.get(
                f"{DATA_SERVICE_URL}/api/v1/symbols",
                params={"broker": broker},
                timeout=5.0
            )
            
            if response.status_code != 200:
                # If pipeline returns 404/500, propagate
                logger.error(f"Failed to fetch symbols: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail=response.text)
            
            return success_response(data=response.json())
            
        except httpx.RequestError as e:
            logger.error(f"Data Service unavailable (Symbols): {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=503, detail=f"Data Service unavailable: {str(e)}")
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Fetch symbols failed: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")

@router.post("/symbols", status_code=201)
async def create_symbol(
    payload: dict,
):
    """
    Create/Register a symbol in the pipeline.
    """
    async with await get_internal_client() as client:
        try:
            response = await client.post(
                f"{DATA_SERVICE_URL}/api/v1/symbols",
                json=payload,
                timeout=5.0
            )
            
            if response.status_code != 201 and response.status_code != 200:
                logger.error(f"Failed to create symbol: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail=response.text)
            
            return success_response(data=response.json())
            
        except httpx.RequestError as e:
            logger.error(f"Data Service unavailable (Create Symbol): {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=503, detail=f"Data Service unavailable: {str(e)}")
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Create symbol failed: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Creation failed: {str(e)}")

@router.patch("/symbols/{symbol_id}")
async def update_symbol_status(
    symbol_id: str,
    payload: dict,
):
    """
    Update symbol status. Proxies to Data Pipeline.
    """
    async with await get_internal_client() as client:
        try:
            response = await client.patch(
                f"{DATA_SERVICE_URL}/api/v1/symbols/{symbol_id}",
                json=payload,
                timeout=5.0
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to update symbol: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail=response.text)
            
            return success_response(data=response.json())
            
        except httpx.RequestError as e:
            logger.error(f"Data Service unavailable (Update Symbol): {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=503, detail=f"Data Service unavailable: {str(e)}")
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Update symbol failed: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

@router.get("/tick/{symbol}")
async def get_latest_tick(
    symbol: str,
    current_user = Depends(get_current_user)
):
    """
    Get the latest tick data for a symbol directly from Redis (ECST).
    Optimized to bypass proxying to Data Pipeline.
    """
    import time
    try:
        r = await redis_client.get_client()
        # Normalize symbol
        norm_symbol = symbol.replace("_", "").replace("/", "").upper()
        
        # Try multiple key formats (CTRADER, OANDA)
        cache_keys = [
            f"market_data:spot:CTRADER:{norm_symbol}",
            f"market_data:spot:OANDA:{norm_symbol}"
        ]
        
        snapshot = {}
        for key in cache_keys:
            temp = await r.hgetall(key)
            if temp and "bid" in temp:
                snapshot = temp
                break
        
        if not snapshot or "bid" not in snapshot:
            # Fallback to proxying if Redis is missing (optional, but safer)
            async with await get_internal_client() as client:
                response = await client.get(
                    f"{DATA_SERVICE_URL}/api/v1/market/tick/{norm_symbol}",
                    timeout=5.0
                )
                if response.status_code == 200:
                    return success_response(data=response.json())
            
            raise HTTPException(status_code=404, detail=f"Tick data not found for {symbol}")
            
        # Parse result
        return success_response(data={
            "symbol": norm_symbol,
            "bid": float(snapshot["bid"]),
            "ask": float(snapshot["ask"]),
            "ts": float(snapshot.get("ts", 0)),
            "source": snapshot.get("source", "unknown")
        })
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Direct Tick Fetch failed for {symbol}: {e}")
        # Final fallback to proxy if something else failed
        async with await get_internal_client() as client:
            try:
                response = await client.get(f"{DATA_SERVICE_URL}/api/v1/market/tick/{symbol.upper()}", timeout=5.0)
                if response.status_code == 200:
                    return success_response(data=response.json())
            except: pass
        raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")

@router.get("/history/pit")
async def get_pit_historical_data(
    symbol: str = Query(..., description="Symbol (e.g., XAUUSD)"),
    timeframe: str = Query(..., description="Timeframe (e.g., 15m)"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get Point-in-Time (PIT) historical data with AI labels.
    Direct DB access for institutional-grade auditability.
    """
    from app.models.candle import Candle
    from sqlalchemy import and_
    
    try:
        query = db.query(Candle).filter(
            and_(
                Candle.symbol == symbol.strip().upper(),
                Candle.timeframe == timeframe
            )
        )
        
        if start_date:
            query = query.filter(Candle.timestamp >= start_date)
        if end_date:
            query = query.filter(Candle.timestamp <= end_date)
            
        results = query.order_by(Candle.timestamp.desc()).limit(limit).all()
        
        data = [
            {
                "timestamp": c.timestamp.isoformat(),
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "volume": float(c.volume) if c.volume else 0,
                "ai_labels": c.ai_labels if hasattr(c, 'ai_labels') else {},
                "regime_tag": c.regime_tag if hasattr(c, 'regime_tag') else None
            }
            for c in reversed(results)
        ]
        
        return success_response(data=data)
    except Exception as e:
        logger.error(f"PIT History failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")
