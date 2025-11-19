"""
StrategyRun SQLAlchemy model.
Source of truth: specs/01_data_model.yaml -> StrategyRun entity
"""

from sqlalchemy import Column, String, Date, DateTime, Numeric, Integer, Enum as SQLEnum, CheckConstraint, Text, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
import enum
from app.database import Base


class RunStatus(enum.Enum):
    """Strategy run execution status"""
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StrategyRun(Base):
    """
    Backtest run results and performance metrics.

    Stores results from Vectorbt parameter sweeps and tracks
    success criteria (G2: Sharpe > 0.8, MDD < 15%).
    """
    __tablename__ = "strategy_runs"

    # Primary Key
    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Run Identification
    strategy_name = Column(String(100), nullable=False,
                          comment="Name of the strategy being tested")
    start_date = Column(Date, nullable=False, index=True,
                       comment="Backtest start date")
    end_date = Column(Date, nullable=False, index=True,
                     comment="Backtest end date")

    # Strategy Parameters (JSON storage for flexibility)
    parameters_json = Column(JSONB, nullable=False,
                            comment="Strategy parameters (EMA periods, ATR multiplier, Rv threshold, etc.)")

    # Performance Metrics (G2 Success Criteria: Sharpe > 0.8, MDD < 15%)
    sharpe_ratio = Column(Numeric(10, 4), nullable=True,
                         comment="Sharpe Ratio (target > 0.8)")
    max_drawdown = Column(Numeric(10, 4), nullable=True,
                         comment="Maximum Drawdown percentage (target < 15%)")
    win_rate = Column(Numeric(5, 4), nullable=True,
                     comment="Win rate (winning trades / total trades)")

    # Trade Statistics
    total_trades = Column(Integer, nullable=True,
                         comment="Total number of trades executed")
    winning_trades = Column(Integer, nullable=True,
                           comment="Number of winning trades")
    losing_trades = Column(Integer, nullable=True,
                          comment="Number of losing trades")

    # P&L Metrics
    total_pnl_usd = Column(Numeric(10, 2), nullable=True,
                          comment="Total profit/loss in USD")
    avg_win_usd = Column(Numeric(10, 2), nullable=True,
                        comment="Average winning trade amount")
    avg_loss_usd = Column(Numeric(10, 2), nullable=True,
                         comment="Average losing trade amount")

    # Streak Statistics
    max_consecutive_wins = Column(Integer, nullable=True,
                                 comment="Maximum consecutive winning trades")
    max_consecutive_losses = Column(Integer, nullable=True,
                                   comment="Maximum consecutive losing trades")

    # Run Status
    status = Column(SQLEnum(RunStatus), nullable=False, default=RunStatus.RUNNING,
                   comment="Run execution status")
    error_message = Column(Text, nullable=True,
                          comment="Error message if run failed")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                       comment="Run start timestamp")
    completed_at = Column(DateTime(timezone=True), nullable=True,
                         comment="Run completion timestamp")

    # Relationship to Trades
    trades = relationship("Trade", back_populates="strategy_run",
                         cascade="all, delete-orphan")

    # Table constraints
    __table_args__ = (
        CheckConstraint('end_date >= start_date', name='check_valid_date_range'),
        Index('ix_strategy_runs_dates', 'start_date', 'end_date'),
        Index('ix_strategy_runs_created_at', 'created_at'),
        {'comment': 'Backtest run results and performance metrics'}
    )

    def __repr__(self):
        return f"<StrategyRun {self.run_id} {self.strategy_name} {self.status.value} sharpe={self.sharpe_ratio}>"
