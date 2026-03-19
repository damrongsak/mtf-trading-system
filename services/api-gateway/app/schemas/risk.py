from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
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
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    account_balance: Optional[float] = Field(None, description="Account Balance in USD")
    risk_percentage: Optional[float] = Field(1.0, description="Risk per trade in % (default 1%)")
    risk_usd: Optional[float] = Field(None, description="Risk in USD (overrides percentage)")

class RiskCheckResponse(BaseModel):
    symbol: str
    direction: str
    risk_reward_ratio: float
    position_size: Dict[str, Any]
    financials: Dict[str, Any]
    is_safe: bool
    warnings: List[str] = []
