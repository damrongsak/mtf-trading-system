from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from app.models.journal import GameLevel

class MentalStateBase(BaseModel):
    greed_level: int = Field(0, ge=0, le=10)
    fear_level: int = Field(0, ge=0, le=10)
    tilt_level: int = Field(0, ge=0, le=10)
    confidence_level: int = Field(0, ge=0, le=10)
    discipline_level: int = Field(0, ge=0, le=10)
    
    class Config:
        from_attributes = True

class TimelineEventBase(BaseModel):
    type: str # TRIGGER, THOUGHT, EMOTION, BEHAVIOR
    description: str
    order_index: int
    
    class Config:
        from_attributes = True

class RootCauseAnalysisBase(BaseModel):
    problem: Optional[str] = None
    why_exist: Optional[str] = None
    flaw: Optional[str] = None
    correction: Optional[str] = None
    logic: Optional[str] = None
    
    class Config:
        from_attributes = True

class JournalEntryCreate(BaseModel):
    # Technical
    symbol: str
    direction: str
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    pnl_amount: Optional[float] = None
    pnl_r: Optional[float] = None
    
    # Risk
    risk_amount: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    
    # Context
    session: Optional[str] = None
    context_score: Optional[int] = Field(None, ge=1, le=10)
    
    # Game Level
    game_level: Optional[GameLevel] = None
    
    # Nested Data
    mental_state: Optional[MentalStateBase] = None
    timeline_events: List[TimelineEventBase] = []
    root_cause: Optional[RootCauseAnalysisBase] = None

class JournalEntryResponse(JournalEntryCreate):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class JournalEntryUpdate(JournalEntryCreate):
    pass


# ==========================
# Analytics Schemas
# ==========================

class JournalStatsResponse(BaseModel):
    total_trades: int
    win_rate: float
    profit_factor: float
    net_pnl: float
    avg_win: float
    avg_loss: float
    max_drawdown: float

class EquityCurvePoint(BaseModel):
    timestamp: datetime
    balance: float
    pnl: float

class PatternItem(BaseModel):
    name: str # e.g. "Game Level A" or "Greed"
    count: int
    avg_pnl: float

class PatternAnalysisResponse(BaseModel):
    game_levels: List[PatternItem]
    top_emotions: List[PatternItem]
    top_mistakes: List[PatternItem] # From Root Cause Analysis

class JournalImportRequest(BaseModel):
    trade_ids: List[UUID]

class JournalImportResponse(BaseModel):
    imported_count: int
    skipped_count: int
    message: str
