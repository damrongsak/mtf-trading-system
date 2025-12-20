"""
StrategyRun Pydantic schemas for API request/response validation.
Source of truth: specs/03_data_model.yaml -> StrategyRun entity
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import UUID
from enum import Enum


class RunStatus(str, Enum):
    """Strategy run execution status."""
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StrategyRunBase(BaseModel):
    """Base strategy run schema."""
    strategy_name: str = Field(..., max_length=100, description="Name of the strategy")
    start_date: date = Field(..., description="Backtest start date")
    end_date: date = Field(..., description="Backtest end date")
    parameters_json: Dict[str, Any] = Field(..., description="Strategy parameters")

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: date, info) -> date:
        """Ensure end_date >= start_date."""
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError("End date must be after or equal to start date")
        return v


class StrategyRunCreate(StrategyRunBase):
    """Schema for creating a new strategy run."""
    pass


class StrategyRunUpdate(BaseModel):
    """Schema for updating strategy run results."""
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe Ratio")
    max_drawdown: Optional[Decimal] = Field(None, description="Maximum Drawdown %")
    win_rate: Optional[Decimal] = Field(None, description="Win rate")
    total_trades: Optional[int] = None
    winning_trades: Optional[int] = None
    losing_trades: Optional[int] = None
    total_pnl_usd: Optional[Decimal] = Field(None)
    avg_win_usd: Optional[Decimal] = Field(None)
    avg_loss_usd: Optional[Decimal] = Field(None)
    max_consecutive_wins: Optional[int] = None
    max_consecutive_losses: Optional[int] = None
    status: Optional[RunStatus] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


class StrategyRunResponse(StrategyRunBase):
    """Schema for strategy run API responses."""
    run_id: UUID
    sharpe_ratio: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    win_rate: Optional[Decimal] = None
    total_trades: Optional[int] = None
    winning_trades: Optional[int] = None
    losing_trades: Optional[int] = None
    total_pnl_usd: Optional[Decimal] = None
    avg_win_usd: Optional[Decimal] = None
    avg_loss_usd: Optional[Decimal] = None
    max_consecutive_wins: Optional[int] = None
    max_consecutive_losses: Optional[int] = None
    status: RunStatus
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BacktestScorecard(BaseModel):
    """Schema for backtest scorecard (F3.3)."""
    run_id: UUID
    strategy_name: str
    period: str = Field(..., description="e.g., '2021-01-01 to 2024-01-01'")

    # G2 Success Criteria
    sharpe_ratio: Optional[Decimal] = Field(None, description="Target > 0.8")
    max_drawdown: Optional[Decimal] = Field(None, description="Target < 15%")
    win_rate: Optional[Decimal] = None

    # Trade Statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl_usd: Decimal

    # Risk Metrics
    avg_risk_per_trade_usd: Decimal = Field(..., description="Should never exceed $10")
    max_risk_per_trade_usd: Decimal = Field(..., description="Should never exceed $10 (G1)")

    # Performance Metrics
    avg_win_usd: Optional[Decimal] = None
    avg_loss_usd: Optional[Decimal] = None
    profit_factor: Optional[Decimal] = Field(None, description="Gross profit / Gross loss")

    # Success Indicators
    passes_g2_criteria: bool = Field(..., description="Sharpe > 0.8 AND MDD < 15%")
    passes_g1_criteria: bool = Field(..., description="Zero violations of $10 risk cap")
