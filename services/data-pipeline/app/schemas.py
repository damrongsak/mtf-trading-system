from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Any
from uuid import UUID
import re

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

    @field_validator('symbol')
    def validate_symbol(cls, v):
        if not re.match(r'^[A-Z0-9_]+$', v):
            raise ValueError('Symbol must contain only uppercase letters, numbers, and underscores')
        return v

    @field_validator('from_date', 'to_date')
    def validate_dates(cls, v):
        if v:
            try:
                # Basic ISO format check
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError('Date must be in ISO format (YYYY-MM-DDTHH:MM:SS)')
        return v

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
    is_active: Optional[bool] = None
    details: Optional[dict] = None

class MarketSymbolCreate(BaseModel):
    symbol: str
    broker: str

class MarketSymbolResponse(BaseModel):
    id: UUID
    symbol: str
    display_name: Optional[str]
    is_active: bool
    data_source_id: Optional[UUID]
    details: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)

# -------------------------------------------------------------------------
# Open Interest Schemas
# -------------------------------------------------------------------------

class OpenInterestSnapshotResponse(BaseModel):
    snapshot_at: datetime
    count: int
    created_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

class OpenInterestRecordResponse(BaseModel):
    contract_symbol: str
    dte: int
    strike: float
    call_oi: float
    put_oi: float

    model_config = ConfigDict(from_attributes=True)

class AnalysisSummary(BaseModel):
    total_call_oi: float
    total_put_oi: float
    pcr: float
    max_call_strike: float
    max_put_strike: float

class AnalysisDistribution(BaseModel):
    strike: float
    call_oi: float
    put_oi: float
    net_delta: float

class OpenInterestAnalysisResponse(BaseModel):
    summary: AnalysisSummary
    distribution: List[AnalysisDistribution]

class SymbolDiscoveryRequest(BaseModel):
    provider: str
    config: dict
