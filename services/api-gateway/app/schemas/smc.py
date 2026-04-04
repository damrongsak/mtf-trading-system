from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class SMCChecklistItem(BaseModel):
    status: bool
    value: str
    comment: str

class SMCVisuals(BaseModel):
    poi_zone: Optional[Dict[str, float]] = None
    trigger_level: float
    stop_loss: float
    take_profit: float
    timeframes: Optional[Dict[str, str]] = None

class SMCDebugInfo(BaseModel):
    last_candle_ts: datetime
    processing_ms: float
    data_source: str

class SMCAnalysisRequest(BaseModel):
    symbol: str = Field(..., example="XAUUSD")
    timeframes: List[str] = Field(default=["H4", "H1", "M15"], example=["H4", "H1", "M15"])
    fund_id: Optional[str] = None
    # For internal use/backtesting
    candles: Optional[Dict[str, Dict[str, List[Dict[str, Any]]]]] = None

class SMCAnalysisResponse(BaseModel):
    summary: str
    confluence_score: int
    is_case_b: bool
    bias: str
    checklist: Dict[str, SMCChecklistItem]
    scenario_analysis: List[str] = []
    visuals: SMCVisuals
    metrics: Optional[Dict[str, Any]] = None
    debug_info: SMCDebugInfo
    timestamp: datetime = Field(default_factory=datetime.utcnow)
