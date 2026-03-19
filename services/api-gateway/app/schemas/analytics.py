from pydantic import BaseModel, Field
from typing import List, Dict, Optional
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
