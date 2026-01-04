from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import shutil
import os
from app.database import get_db
from sqlalchemy import func, desc
from app.services.loader import load_candles_from_csv
from app.models.candle import Candle
from app.models.market import MarketSymbol
from app.models.data_source import DataSource
from app.schemas import CandleResponse, PaginationResponse, BackfillRequest, BackfillResponse, MarketSymbolResponse, MarketSymbolUpdate
from app.scheduler.jobs import run_ingestion_job
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime
import logging
import traceback
from app.services.open_interest_service import OpenInterestService
import uuid

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

@router.get("/ingest/open-interest/snapshots", response_model=List[dict])
def get_open_interest_snapshots(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get list of available Open Interest snapshots.
    """
    from app.models.open_interest import OpenInterest
    
    # Aggregate by snapshot_at
    results = db.query(
        OpenInterest.snapshot_at,
        func.count(OpenInterest.id).label('count'),
        func.max(OpenInterest.created_at).label('created_at')
    ).group_by(OpenInterest.snapshot_at)\
     .order_by(desc(OpenInterest.snapshot_at))\
     .limit(limit)\
     .all()
    
    return [
        {
            "snapshot_at": r.snapshot_at, 
            "count": r.count, 
            "created_at": r.created_at
        } 
        for r in results
    ]

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

    # Validate Symbol Exists
    market_symbol = db.query(MarketSymbol).filter(MarketSymbol.symbol == symbol).first()
    if not market_symbol:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not registered in MarketSymbols.")

    temp_file = f"temp_{file.filename}"
    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Load candles with validation
        try:
            df = load_candles_from_csv(temp_file, symbol, timeframe)
        except ValueError as ve:
             raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
             logger.error(f"Processing error in load_candles_from_csv: {str(e)}")
             logger.error(traceback.format_exc()) # Log full traceback
             raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
        
        # Convert DataFrame rows to Candle objects
        candle_dicts = []
        now = datetime.utcnow()
        for _, row in df.iterrows():
            candle_dicts.append({
                "id": uuid.uuid4(),
                "market_symbol_id": market_symbol.id,
                "timeframe": row['timeframe'],
                "timestamp": row['timestamp'],
                "open": row['open'],
                "high": row['high'],
                "low": row['low'],
                "close": row['close'],
                "volume": row['volume'],
                "created_at": now,
                "updated_at": now
            })

        # Save to database using upsert logic
        if candle_dicts:
            stmt = insert(Candle).values(candle_dicts)
            do_update_stmt = stmt.on_conflict_do_update(
                index_elements=['market_symbol_id', 'timeframe', 'timestamp'],
                set_={
                    'open': stmt.excluded.open,
                    'high': stmt.excluded.high,
                    'low': stmt.excluded.low,
                    'close': stmt.excluded.close,
                    'volume': stmt.excluded.volume,
                    'updated_at': datetime.utcnow()
                }
            )
            try:
                db.execute(do_update_stmt)
                db.commit()
            except Exception as db_err:
                db.rollback()
                logger.error(f"Database upsert error: {str(db_err)}")
                logger.error(traceback.format_exc()) 
                raise HTTPException(status_code=500, detail=f"Database upsert error: {str(db_err)}")
        
        return {"message": f"Successfully processed {len(df)} rows for {symbol} {timeframe}"}
    except HTTPException as he:
        raise he
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
    # 1. Resolve the specific MarketSymbol for this Broker + Symbol combo
    market_symbol = db.query(MarketSymbol).join(DataSource).filter(
        MarketSymbol.symbol == symbol,
        DataSource.name == broker
    ).first()

    # Retry with underscore if slash provided (e.g. XAU/USD -> XAU_USD)
    if not market_symbol and "/" in symbol:
        normalized_symbol = symbol.replace("/", "_")
        market_symbol = db.query(MarketSymbol).join(DataSource).filter(
            MarketSymbol.symbol == normalized_symbol,
            DataSource.name == broker
        ).first()

    if not market_symbol:
        # If specific broker not found, check if symbol exists at all to give better error
        any_symbol = db.query(MarketSymbol).filter(MarketSymbol.symbol == symbol).first()
        if any_symbol:
             # Symbol exists but not for this broker
             return PaginationResponse(total=0, page=page, page_size=page_size, data=[])
        else:
             # Symbol doesn't exist at all
             return PaginationResponse(total=0, page=page, page_size=page_size, data=[])

    # 2. Query Candles for this specific MarketSymbol
    query = db.query(Candle).filter(
        Candle.market_symbol_id == market_symbol.id,
        Candle.timeframe == timeframe
    )
    
    total = query.count()
    candles = query.order_by(Candle.timestamp.desc())\
                   .offset((page - 1) * page_size)\
                   .limit(page_size)\
                   .all()
    
    # Inject 'symbol' and 'broker' into response
    data = []
    for c in candles:
        c_dict = {
            "id": c.id,
            "symbol": symbol,
            "broker": broker, # We know this matches the query
            "timeframe": c.timeframe,
            "timestamp": c.timestamp,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
            "ema_9_4h": c.ema_9_4h,
            "ema_200_4h": c.ema_200_4h,
            "ema_200_d": c.ema_200_d,
            "atr_14_15m": c.atr_14_15m,
            "body_to_wick_ratio": c.body_to_wick_ratio
        }
        data.append(c_dict)

    return PaginationResponse(
        total=total,
        page=page,
        page_size=page_size,
        data=data
    )

@router.get("/symbols", response_model=List[MarketSymbolResponse])
def get_active_symbols(
    broker: str = Query("OANDA", description="Filter by broker name"),
    db: Session = Depends(get_db)
):
    """
    Get list of active symbols for a specific broker.
    Used for batch analysis auto-discovery.
    """
    symbols = db.query(MarketSymbol).join(DataSource).filter(
        DataSource.name == broker
    ).order_by(MarketSymbol.is_active.desc(), MarketSymbol.symbol).all()
    
    return symbols

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
    symbol = db.query(MarketSymbol).filter(MarketSymbol.id == symbol_id).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not found")
        
    symbol.is_active = update_data.is_active
    db.commit()
    db.refresh(symbol)
    
    return symbol
