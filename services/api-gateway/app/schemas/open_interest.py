from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

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
