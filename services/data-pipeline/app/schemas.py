from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

class CandleBase(BaseModel):
    symbol: str
    timeframe: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

class CandleCreate(CandleBase):
    pass

from uuid import UUID

class CandleResponse(CandleBase):
    id: UUID
    ema_9_4h: Optional[Decimal] = None
    ema_200_4h: Optional[Decimal] = None
    ema_200_d: Optional[Decimal] = None
    atr_14_15m: Optional[Decimal] = None
    body_to_wick_ratio: Optional[Decimal] = None

    class Config:
        from_attributes = True

class PaginationResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data: List[CandleResponse]
