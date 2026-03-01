"""
Trade SQLAlchemy model.
Source of truth: specs/03_data_model.yaml -> Trade entity
"""

from sqlalchemy import Column, String, DateTime, Numeric, Integer, Enum as SQLEnum, ForeignKey, Index, func, CheckConstraint, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
import enum
from app.database import Base


class TradeStatus(enum.Enum):
    """Trade execution status"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"


class TradeDirection(enum.Enum):
    """Trade direction"""
    LONG = "LONG"
    SHORT = "SHORT"


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = {"extend_existing": True}

    trade_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_run_id = Column(UUID(as_uuid=True), ForeignKey("strategy_runs.run_id"), nullable=True, index=True)
    broker_account_id = Column(UUID(as_uuid=True), ForeignKey("broker_accounts.id"), nullable=True, index=True)
    
    symbol = Column(String(20), nullable=False, index=True)
    strategy_name = Column(String(100), nullable=False,
                          comment="Name of the strategy that generated the signal")
    signal_timestamp = Column(DateTime(timezone=True), nullable=False, index=True,
                             comment="Timestamp when the signal was generated")

    # Status and Rejection Tracking
    status = Column(SQLEnum(TradeStatus), nullable=False, index=True,
                   comment="Trade execution status (REJECTED tracks risk violations)")
    rejection_reason = Column(String(500), nullable=True,
                             comment="Reason for trade rejection (e.g., 'Risk exceeds $10 cap')")

    # Trade Details
    direction = Column(SQLEnum(TradeDirection), nullable=False,
                      comment="Trade direction")
    entry_price = Column(Numeric(18, 8), nullable=False,
                        comment="Planned or actual entry price")
    sl_price = Column(Numeric(18, 8), nullable=False,
                     comment="Stop loss price")
    tp_price = Column(Numeric(18, 8), nullable=False,
                     comment="Take profit price")

    # Position Sizing & Risk (Critical for F2.1-F2.4)
    lot_size = Column(Numeric(12, 6), nullable=False,
                     comment="Calculated lot size (must be >= 0.01)")
    commission = Column(Numeric(10, 2), nullable=True,
                       comment="Trading commission in USD")
    risk_usd = Column(Numeric(10, 2), nullable=False,
                     comment="Calculated risk in USD (must be <= $10)")
    atr_pips = Column(Numeric(10, 2), nullable=True,
                     comment="ATR-based stop loss distance in pips")
    rr_ratio = Column(Numeric(5, 2), nullable=True,
                     comment="Risk-to-reward ratio (minimum 1:2)")

    # Performance Tracking
    pnl_usd = Column(Numeric(10, 2), nullable=True,
                    comment="Realized profit/loss in USD (for closed trades)")
    mae_usd = Column(Numeric(10, 2), nullable=True,
                    comment="Maximum Adverse Excursion in USD")
    mfe_usd = Column(Numeric(10, 2), nullable=True,
                    comment="Maximum Favorable Excursion in USD")

    # Exit Details
    exit_price = Column(Numeric(18, 8), nullable=True,
                       comment="Actual exit price (for closed trades)")
    exit_timestamp = Column(DateTime(timezone=True), nullable=True,
                           comment="Timestamp when the trade was closed")

    # Additional Metadata (Confluence zones, indicators, etc.)
    metadata_json = Column(JSONB, nullable=True,
                          comment="Additional trade metadata (confluence zones, indicators, etc.)")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                       comment="Record creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                       onupdate=func.now(),
                       comment="Record last update timestamp")

    # Relationship to StrategyRun
    strategy_run = relationship("StrategyRun", back_populates="trades")

    # Table constraints (from specs/03_data_model.yaml validation_rules)
    __table_args__ = (
        CheckConstraint('risk_usd <= 10.00', name='check_risk_cap'),
        CheckConstraint('lot_size > 0', name='check_min_lot_size'),
        CheckConstraint('atr_pips <= 100.0 OR atr_pips IS NULL', name='check_max_atr_pips'),
        CheckConstraint('rr_ratio >= 2.0 OR rr_ratio IS NULL', name='check_min_rr_ratio'),
        {
            'comment': 'Individual trade records with risk and execution details',
            'extend_existing': True
        }
    )

    def __repr__(self):
        return f"<Trade {self.trade_id} {self.symbol} {self.direction.value} {self.status.value} risk=${self.risk_usd}>"
