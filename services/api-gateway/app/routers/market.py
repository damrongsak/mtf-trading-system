from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models.candle import Candle
from app.schemas.response import APIResponse, ResponseStatus
from pydantic import BaseModel

router = APIRouter(
    tags=["market"]
)

class CandleRes(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    class Config:
        from_attributes = True

@router.get("/candles", response_model=APIResponse[List[CandleRes]])
async def get_candles(
    symbol: str = Query(..., description="Symbol (e.g. EUR_USD)"),
    timeframe: str = Query(..., description="Timeframe (e.g. H1)"),
    count: int = Query(500, description="Number of candles to return"),
    from_time: Optional[datetime] = Query(None, description="Start time"),
    to_time: Optional[datetime] = Query(None, description="End time"),
    db: Session = Depends(get_db)
):
    query = db.query(Candle).filter(
        Candle.symbol == symbol,
        Candle.timeframe == timeframe
    )

    if from_time:
        query = query.filter(Candle.timestamp >= from_time)
    if to_time:
        query = query.filter(Candle.timestamp <= to_time)
    
    # Get latest candles
    # To get "last 500", need to sort desc, limit, then maybe reverse?
    # but efficiently, we just return them. Client can reverse if needed, or we reverse.
    # Usually charts expect time ascending.
    
    candles = query.order_by(desc(Candle.timestamp)).limit(count).all()
    
    # Reverse to return oldest first
    candles.reverse()
    
    return APIResponse(
        status=ResponseStatus.SUCCESS,
        data=candles
    )
