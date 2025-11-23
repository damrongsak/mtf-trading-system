from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import shutil
import os
from app.database import get_db
from app.services.loader import load_candles_from_csv
from app.models.candle import Candle
from app.schemas import CandleResponse, PaginationResponse

router = APIRouter()

@router.post("/upload_csv", status_code=201)
async def upload_csv(
    file: UploadFile = File(...),
    symbol: str = Query(..., description="Symbol (e.g., XAUUSD)"),
    timeframe: str = Query(..., description="Timeframe (e.g., 15m)"),
    db: Session = Depends(get_db)
):
    """
    Upload a CSV file containing OHLCV data.
    The file is saved temporarily, processed, and then deleted.
    """
    temp_file = f"temp_{file.filename}"
    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Load candles using the existing service
        df = load_candles_from_csv(temp_file, symbol, timeframe)
        
        # Save to database
        candles = []
        for _, row in df.iterrows():
            candle = Candle(
                symbol=row['symbol'],
                timeframe=row['timeframe'],
                timestamp=row['timestamp'],
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row['volume']
            )
            candles.append(candle)
        
        # Bulk save could be better, but simple add_all for now
        db.add_all(candles)
        db.commit()
        
        return {"message": f"Successfully loaded data for {symbol} {timeframe}"}
    except Exception as e:
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
