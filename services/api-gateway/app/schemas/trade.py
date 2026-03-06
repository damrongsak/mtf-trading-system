"""
Trade Pydantic schemas for API request/response validation.
Source of truth: specs/03_data_model.yaml -> Trade entity
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import UUID
from enum import Enum


class TradeStatus(str, Enum):
    """Trade execution status."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"


class TradeDirection(str, Enum):
    """Trade direction."""
    LONG = "LONG"
    SHORT = "SHORT"


class TradeBase(BaseModel):
    """Base trade schema with common fields."""
    symbol: str = Field(..., max_length=20, description="Trading pair symbol (e.g., XAU/USD)")
    strategy_name: str = Field(..., max_length=100, description="Name of the strategy")
    signal_timestamp: datetime = Field(..., description="Timestamp when signal was generated")
    direction: TradeDirection = Field(..., description="Trade direction (LONG/SHORT)")
    entry_price: Decimal = Field(..., description="Entry price")
    sl_price: Decimal = Field(..., description="Stop loss price")
    tp_price: Decimal = Field(..., description="Take profit price")


class TradeCreate(TradeBase):
    """Schema for creating a new trade (signal proposal)."""
    strategy_run_id: Optional[UUID] = Field(None, description="Link to strategy run")
    lot_size: Decimal = Field(..., description="Calculated lot size", ge=0.01)
    risk_usd: Decimal = Field(..., description="Calculated risk in USD", le=10.00)
    atr_pips: Optional[Decimal] = Field(None, description="ATR-based SL distance in pips", le=100.0)
    rr_ratio: Optional[Decimal] = Field(None, description="Risk-to-reward ratio", ge=2.0)
    metadata_json: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator('risk_usd')
    @classmethod
    def validate_risk_cap(cls, v: Decimal) -> Decimal:
        """Enforce F2.2: $10 risk cap."""
        if v > Decimal("10.00"):
            raise ValueError("Risk per trade must not exceed $10 (F2.2)")
        return v

    @field_validator('lot_size')
    @classmethod
    def validate_min_lot(cls, v: Decimal) -> Decimal:
        """Enforce F2.3: 0.01 minimum lot."""
        if v < Decimal("0.01"):
            raise ValueError("Lot size must be at least 0.01 (F2.3)")
        return v

    @field_validator('atr_pips')
    @classmethod
    def validate_max_atr(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Enforce F2.4: 100 pips max ATR SL."""
        if v is not None and v > Decimal("100.0"):
            raise ValueError("ATR-based stop loss must not exceed 100 pips (F2.4)")
        return v


class TradeUpdate(BaseModel):
    """Schema for updating trade status and exit details."""
    status: Optional[TradeStatus] = None
    rejection_reason: Optional[str] = Field(None, max_length=500)
    exit_price: Optional[Decimal] = Field(None)
    exit_timestamp: Optional[datetime] = None
    pnl_usd: Optional[Decimal] = Field(None)
    mae_usd: Optional[Decimal] = Field(None)
    mfe_usd: Optional[Decimal] = Field(None)


class TradeResponse(TradeBase):
    """Schema for trade API responses."""
    trade_id: UUID
    strategy_run_id: Optional[UUID] = None
    status: TradeStatus
    rejection_reason: Optional[str] = None
    lot_size: Decimal
    risk_usd: Decimal
    atr_pips: Optional[Decimal] = None
    rr_ratio: Optional[Decimal] = None
    pnl_usd: Optional[Decimal] = None
    mae_usd: Optional[Decimal] = None
    mfe_usd: Optional[Decimal] = None
    exit_price: Optional[Decimal] = None
    exit_timestamp: Optional[datetime] = None
    broker_trade_id: Optional[str] = None
    broker_deal_id: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskCheckRequest(BaseModel):
    """Schema for risk validation endpoint (US3)."""
    symbol: str
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    account_balance: Optional[float] = Field(None, description="Account Balance in USD")
    risk_percentage: Optional[float] = Field(1.0, description="Risk per trade in % (default 1%)")
    risk_usd: Optional[float] = Field(None, description="Risk in USD (overrides percentage)")


class RiskCheckResponse(BaseModel):
    """Schema for risk validation response."""
    data: Dict[str, Any]
