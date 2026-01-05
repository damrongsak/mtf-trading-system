from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging
import traceback
import uuid
import shutil
import os
from app.database import get_db
from app.services.market_service import MarketService
from app.services.candle_service import CandleService
from app.services.open_interest_service import OpenInterestService
from app.scheduler.jobs import run_ingestion_job

from app.schemas import (
    CandleResponse, 
    PaginationResponse, 
    BackfillRequest, 
    BackfillResponse, 
    MarketSymbolResponse, 
    MarketSymbolUpdate,
    OpenInterestSnapshotResponse,
    OpenInterestRecordResponse,
    OpenInterestAnalysisResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

@router.post("/backfill", response_model=BackfillResponse, status_code=202)
async def trigger_backfill(
    request: BackfillRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger a historical data backfill job.
    """
    from_date_obj = datetime.fromisoformat(request.from_date) if request.from_date else None
    to_date_obj = datetime.fromisoformat(request.to_date) if request.to_date else None
    
    background_tasks.add_task(
        run_ingestion_job, 
        symbols=[request.symbol], 
        from_date=from_date_obj, 
        to_date=to_date_obj
    )
    
    return BackfillResponse(
        message=f"Backfill triggered for {request.symbol} {request.timeframe}",
        job_id=str(uuid.uuid4())
    )

@router.post("/ingest/manual", status_code=202)
async def trigger_ingestion(
    background_tasks: BackgroundTasks,
    symbol: Optional[str] = Query(None, description="Optional symbol to ingest (e.g., EUR_USD)"),
    from_date: Optional[datetime] = Query(None, description="Start date for backfill (ISO format)"),
    to_date: Optional[datetime] = Query(None, description="End date for backfill (ISO format)")
):
    """
    Manually trigger the data ingestion job in the background.
    """
    symbols = [symbol] if symbol else None
    background_tasks.add_task(run_ingestion_job, symbols, from_date, to_date)
    return {"message": "Ingestion job triggered in background"}

@router.post("/ingest/open-interest", status_code=201)
async def ingest_open_interest(
    file: UploadFile = File(...),
    snapshot_at: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Ingest Open Interest Matrix Excel file.
    """
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx).")

    try:
        content = await file.read()
        result = OpenInterestService.parse_and_store(content, db, snapshot_at)
        return result
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@router.get("/ingest/open-interest/snapshots", response_model=List[OpenInterestSnapshotResponse])
def get_open_interest_snapshots(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get list of available Open Interest snapshots.
    """
    return OpenInterestService.get_snapshots(db, limit)

@router.get("/ingest/open-interest/details", response_model=List[OpenInterestRecordResponse])
def get_open_interest_details(
    snapshot_at: datetime = Query(..., description="Snapshot timestamp"),
    contract: Optional[str] = Query(None, description="Filter by contract symbol"),
    min_oi: int = Query(0, description="Minimum Open Interest filter"),
    max_oi: Optional[int] = Query(None, description="Maximum Open Interest filter"),
    smart_filter: bool = Query(False, description="Apply smart range filtering (std dev)"),
    db: Session = Depends(get_db)
):
    """
    Get detailed Open Interest records for a specific snapshot.
    """
    return OpenInterestService.get_details(db, snapshot_at, contract, min_oi, max_oi, smart_filter)

@router.get("/ingest/open-interest/analysis", response_model=OpenInterestAnalysisResponse)
def get_open_interest_analysis(
    snapshot_at: datetime = Query(..., description="Snapshot timestamp"),
    contract: Optional[str] = Query(None, description="Filter by contract symbol"),
    min_oi: int = Query(0, description="Minimum Open Interest filter"),
    max_oi: Optional[int] = Query(None, description="Maximum Open Interest filter"),
    db: Session = Depends(get_db)
):
    """
    Get aggregated analytics for a specific snapshot.
    Returns PCR, Max Levels, and Distribution.
    Supports filtering by contract, min_oi, and max_oi.
    """
    return OpenInterestService.get_analysis(db, snapshot_at, contract, min_oi, max_oi)

@router.get("/ingest/open-interest/contracts", response_model=List[str])
def get_open_interest_contracts(
    snapshot_at: datetime = Query(..., description="Snapshot timestamp"),
    db: Session = Depends(get_db)
):
    """
    Get list of available contracts (expiries) for a specific snapshot.
    """
    return OpenInterestService.get_contracts(db, snapshot_at)

async def upload_candles(
    file: UploadFile = File(...),
    symbol: str = Query(..., description="Symbol (e.g., XAUUSD)"),
    timeframe: str = Query(..., description="Timeframe (e.g., 15m)"),
    db: Session = Depends(get_db)
):
    """
    Upload a CSV file containing OHLCV data.
    Validates schema, data types, and logical consistency.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV.")

    temp_file = f"temp_{file.filename}"
    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return CandleService.process_csv_file(temp_file, symbol, timeframe, db)
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

@router.get("/candles", response_model=PaginationResponse)
def get_candles(
    symbol: str = Query(..., description="Symbol to filter by"),
    timeframe: str = Query(..., description="Timeframe to filter by"),
    broker: str = Query("OANDA", description="Data Provider (e.g. OANDA, BINANCE)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Retrieve candles with pagination. Filters by Symbol AND Broker.
    Defaults to 'OANDA' if broker not specified.
    """
    return CandleService.get_candles(db, symbol, timeframe, broker, page, page_size)

@router.get("/symbols", response_model=List[MarketSymbolResponse])
def get_active_symbols(
    broker: str = Query("OANDA", description="Filter by broker name"),
    db: Session = Depends(get_db)
):
    """
    Get list of active symbols for a specific broker.
    Used for batch analysis auto-discovery.
    """
    return MarketService.get_active_symbols(db, broker)

@router.post("/stream/refresh", status_code=200)
async def refresh_streams():
    """
    Trigger a refresh of the streaming subscriptions.
    """
    from app.streaming.manager import stream_manager
    await stream_manager.refresh_subscriptions()
    return {"message": "Streaming subscriptions refreshed"}

@router.patch("/symbols/{symbol_id}", response_model=MarketSymbolResponse)
def update_symbol_status(
    symbol_id: uuid.UUID,
    update_data: MarketSymbolUpdate,
    db: Session = Depends(get_db)
):
    """
    Update symbol status (is_active).
    """
    return MarketService.update_status(db, symbol_id, update_data)
