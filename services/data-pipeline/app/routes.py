from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import shutil
import os
from app.database import get_db
from app.services.loader import load_candles_from_csv
from app.models.candle import Candle
from app.schemas import CandleResponse, PaginationResponse
from app.scheduler.jobs import run_ingestion_job
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime
import logging
import traceback
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/ingest/manual", status_code=202)
async def trigger_ingestion(
    background_tasks: BackgroundTasks,
    symbol: Optional[str] = Query(None, description="Optional symbol to ingest (e.g., EUR_USD)")
):
    """
    Manually trigger the data ingestion job in the background.
    """
    symbols = [symbol] if symbol else None
    background_tasks.add_task(run_ingestion_job, symbols)
    return {"message": "Ingestion job triggered in background"}

@router.post("/upload", status_code=201)
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
        candle_objects = []
        now = datetime.utcnow()
        for _, row in df.iterrows():
            candle_objects.append(Candle(
                id=uuid.uuid4(), # Generate UUID explicitly
                symbol=row['symbol'],
                timeframe=row['timeframe'],
                timestamp=row['timestamp'],
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row['volume'],
                created_at=now,
                updated_at=now
            ))

        # Save to database using upsert logic
        # Convert Candle objects to dictionaries for the insert statement
        if candle_objects:
            stmt = insert(Candle).values([c.to_dict() for c in candle_objects])
            do_update_stmt = stmt.on_conflict_do_update(
                index_elements=['symbol', 'timeframe', 'timestamp'],
                set_={
                    'open': stmt.excluded.open,
                    'high': stmt.excluded.high,
                    'low': stmt.excluded.low,
                    'close': stmt.excluded.close,
                    'volume': stmt.excluded.volume,
                    'updated_at': datetime.utcnow() # Assuming an updated_at field for candles
                }
            )
            try:
                db.execute(do_update_stmt)
                db.commit()
            except Exception as db_err:
                db.rollback()
                logger.error(f"Database upsert error: {str(db_err)}")
                logger.error(traceback.format_exc()) # Log full traceback
                raise HTTPException(status_code=500, detail=f"Database upsert error: {str(db_err)}")
        
        return {"message": f"Successfully processed {len(df)} rows for {symbol} {timeframe}"}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        logger.error(traceback.format_exc()) # Log full traceback
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

@router.get("/candles", response_model=PaginationResponse)
def get_candles(
    symbol: str = Query(..., description="Symbol to filter by"),
    timeframe: str = Query(..., description="Timeframe to filter by"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Retrieve candles with pagination.
    """
    query = db.query(Candle).filter(
        Candle.symbol == symbol,
        Candle.timeframe == timeframe
    )
    
    total = query.count()
    candles = query.order_by(Candle.timestamp.desc())\
                   .offset((page - 1) * page_size)\
                   .limit(page_size)\
                   .all()
    
    return PaginationResponse(
        total=total,
        page=page,
        page_size=page_size,
        data=candles
    )
