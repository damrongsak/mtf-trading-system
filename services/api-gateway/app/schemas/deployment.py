
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class DeploymentBase(BaseModel):
    fund_id: UUID
    strategy_id: UUID
    stock_symbol: str
    timeframe: str
    config_snapshot: Dict[str, Any]
    is_live: bool = False
    is_shadow: bool = False

class DeploymentCreate(DeploymentBase):
    pass

class DeploymentResponse(DeploymentBase):
    id: UUID
    user_id: UUID
    status: str
    is_shadow: bool = False
    started_at: datetime
    stopped_at: Optional[datetime] = None
    last_signal_at: Optional[datetime] = None
    last_error: Optional[str] = None
    total_pnl_usd: Optional[float] = 0.0
    strategy_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class StrategyLogResponse(BaseModel):
    id: UUID
    deployment_id: UUID
    timestamp: datetime
    essential_output: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)
