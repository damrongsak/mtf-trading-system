from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Any
from uuid import UUID

class HealthCheck(BaseModel):
    status: str
    service: str
    scheduler: str

class BackfillRequest(BaseModel):
    symbol: str
    timeframe: str
    from_date: Optional[str] = None # ISO format
    to_date: Optional[str] = None
    count: Optional[int] = 2500

class BackfillResponse(BaseModel):
    message: str
    job_id: Optional[str]

class CandleResponse(BaseModel):
    id: UUID
    symbol: str
    broker: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    ema_9_4h: Optional[float] = None
    ema_200_4h: Optional[float] = None
    ema_200_d: Optional[float] = None
    atr_14_15m: Optional[float] = None
    body_to_wick_ratio: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class PaginationResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data: List[CandleResponse]

    model_config = ConfigDict(from_attributes=True)

class MarketSymbolUpdate(BaseModel):
    is_active: bool

class MarketSymbolResponse(BaseModel):
    id: UUID
    symbol: str
    display_name: Optional[str]
    is_active: bool
    data_source_id: Optional[UUID]

    model_config = ConfigDict(from_attributes=True)
