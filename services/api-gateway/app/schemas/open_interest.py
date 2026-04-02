from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

class OpenInterestSnapshotResponse(BaseModel):
    snapshot_at: datetime
    count: int
    created_at: Optional[datetime]
    underlying_price: Optional[float] = None

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
    oiwap: float
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

class DriftAnalysis(BaseModel):
    pcr_drift: float
    net_oi_drift: float
    call_wall_shift: float
    put_wall_shift: float
    oiwap_shift: float
    sentiment: str

class UnifiedOIProfileResponse(BaseModel):
    symbol: str
    snapshot_at: datetime
    prev_snapshot_at: Optional[datetime]
    price: float
    gamma_regime: str
    crowding_regime: str
    sentiment_drift: DriftAnalysis
    gamma_levels: List[dict]
    summary: AnalysisSummary

class GEXDistribution(BaseModel):
    strike: float
    dte: int
    call_gex: float
    put_gex: float
    net_gex: float

class OpenInterestGEXResponse(BaseModel):
    snapshot_at: datetime
    spot_price: float
    total_gex: float
    gamma_flip: float
    regime: str
    distribution: List[GEXDistribution]
    nearest_dte: Optional[float] = None
    max_dte: Optional[float] = None
