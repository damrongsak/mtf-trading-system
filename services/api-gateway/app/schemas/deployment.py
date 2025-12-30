
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class DeploymentBase(BaseModel):
    strategy_id: UUID
    stock_symbol: str
    timeframe: str
    config_snapshot: Dict[str, Any]
    is_live: bool = False

class DeploymentCreate(DeploymentBase):
    pass

class DeploymentResponse(DeploymentBase):
    id: UUID
    user_id: UUID
    status: str
    started_at: datetime
    stopped_at: Optional[datetime] = None
    last_signal_at: Optional[datetime] = None
    last_error: Optional[str] = None
    total_pnl_usd: Optional[float] = 0.0
    strategy_name: Optional[str] = None
    
    class Config:
        from_attributes = True
