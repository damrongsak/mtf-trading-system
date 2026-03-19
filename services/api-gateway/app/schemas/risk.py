from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class FundRiskConfig(BaseModel):
    fund_id: UUID
    max_drawdown_threshold: Optional[Decimal] = None
    gross_exposure_limit: Optional[Decimal] = None
    net_exposure_limit: Optional[Decimal] = None
    stop_trading_on_breach: bool = True
    kill_switch_active: bool = False

class RiskAdjustmentRequest(BaseModel):
    max_drawdown_threshold: Optional[Decimal] = None
    gross_exposure_limit: Optional[Decimal] = None
    net_exposure_limit: Optional[Decimal] = None
    stop_trading_on_breach: Optional[bool] = None

class KillSwitchRequest(BaseModel):
    active: bool
    reason: Optional[str] = None

class RiskCheckRequest(BaseModel):
    symbol: str
    units: float
    side: str
    account_id: str
    strategy_id: Optional[str] = None

class RiskCheckResponse(BaseModel):
    is_allowed: bool
    reason: Optional[str] = None
    adjusted_units: Optional[float] = None
    margin_required: Optional[float] = None
    max_drawdown_hit: bool = False
