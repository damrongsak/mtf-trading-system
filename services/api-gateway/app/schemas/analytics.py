from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from uuid import UUID
from datetime import datetime

class LatencyBucket(BaseModel):
    hour: int
    symbol: str
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    count: int

class LatencyHeatmapResponse(BaseModel):
    buckets: List[LatencyBucket]

class PerformanceComparisonItem(BaseModel):
    signal_id: UUID
    symbol: str
    live_pnl: Optional[float] = None
    shadow_pnl: Optional[float] = None
    slippage_usd: Optional[float] = None
    latency_gap_ms: Optional[float] = None

class PerformanceComparisonResponse(BaseModel):
    comparisons: List[PerformanceComparisonItem]

class RejectionReasonSummary(BaseModel):
    reason: str
    count: int
    latest_at: datetime

class ExecutionRejectionResponse(BaseModel):
    rejections: List[RejectionReasonSummary]
    total_rejections: int

class AccountHistoryItem(BaseModel):
    id: UUID
    broker_account_id: UUID
    balance: float
    equity: float
    used_margin: float
    free_margin: float
    margin_level: Optional[float] = None
    unrealized_gross: Optional[float] = None
    unrealized_net: Optional[float] = None
    timestamp: datetime

class AccountHistoryResponse(BaseModel):
    history: List[AccountHistoryItem]

class HRPWeightsResponse(BaseModel):
    fund_id: UUID
    weights: Dict[str, float]
    updated_at: datetime

class DriftAlert(BaseModel):
    type: str
    severity: str = "WARNING"
    fund_id: Optional[str] = None
    account_id: Optional[str] = None
    broker: Optional[str] = None
    symbol: Optional[str] = None
    drift_units: Optional[float] = None
    relative_drift: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime

class DriftAlertsResponse(BaseModel):
    alerts: List[DriftAlert]
