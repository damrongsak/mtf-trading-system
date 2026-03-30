"""
Trade SQLAlchemy model.
Source of truth: specs/03_data_model.yaml -> Trade entity
"""

from sqlalchemy import Column, String, DateTime, Numeric, Integer, Enum as SQLEnum, ForeignKey, Index, func, CheckConstraint, Text, Boolean, BigInteger, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
import enum
from app.database import Base


class TradeStatus(enum.Enum):
    """Trade execution status"""
    OPEN = "OPEN"
    PENDING = "PENDING"
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
    broker_trade_id = Column(String(100), nullable=True, index=True,
                             comment="Official trade ID from broker")
    parent_trade_id = Column(UUID(as_uuid=True), nullable=True, index=True,
                             comment="For child trades (TWAP/VWAP/Partial Close)")
    
    # [PHASE 12] Institutional Order Management
    execution_algo = Column(String(50), nullable=True, comment="Execution algorithm used (TWAP, VWAP, SCALE_IN)")
    algo_params = Column(JSONB, nullable=True, comment="Parameters for the execution algorithm")
    algo_status = Column(String(20), default="NONE", comment="Status of the execution algorithm")
    
    symbol = Column(String(20), nullable=False, index=True)
    strategy_name = Column(String(100), nullable=False,
                          comment="Name of the strategy that generated the signal")
    signal_timestamp = Column(DateTime(timezone=True), nullable=False, index=True,
                             comment="Timestamp when the signal was generated")
    signal_id = Column(UUID(as_uuid=True), nullable=True, index=True,
                        comment="Link to the specific signal that triggered this trade")
    signal_timestamp_ns = Column(BigInteger, nullable=True,
                                 comment="Nanosecond precision timestamp for latency tracking")
    execution_latency_ms = Column(Numeric(10, 4), nullable=True,
                                 comment="Execution latency in milliseconds (Broker Fill - System Signal)")
    slippage_pips = Column(Numeric(10, 2), nullable=True,
                          comment="Slippage in pips (Actual Entry - Planned Entry)")
    slippage_ms = Column(Numeric(10, 4), nullable=True,
                        comment="Broker execution latency (Broker Fill - Broker Order)")
    is_live = Column(Boolean, default=False)  # True = Real Money, False = Paper
    is_shadow = Column(Boolean, default=False, comment="If true, signals are not sent to the broker")

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
    sl_price = Column(Numeric(18, 8), nullable=True,
                     comment="Stop loss price")
    tp_price = Column(Numeric(18, 8), nullable=True,
                     comment="Take profit price")
    trailing_stop = Column(Boolean, default=False, nullable=True,
                          comment="Enable/Disable trailing stop loss")

    # Position Sizing & Risk (Critical for F2.1-F2.4)
    lot_size = Column(Numeric(12, 6), nullable=False,
                     comment="Calculated lot size (must be >= 0.01)")
    commission = Column(Numeric(10, 2), nullable=True,
                       comment="Trading commission in USD (System Estimate or Reconciled)")
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

    # Broker Specifics
    broker_deal_id = Column(String(100), nullable=True, index=True,
                             comment="Stable deal identifier for cTrader deduplication; optional for OANDA")
    swap = Column(Numeric(10, 2), nullable=True)
    gross_pnl = Column(Numeric(10, 2), nullable=True)
    broker_raw_pnl = Column(Numeric(18, 2), nullable=True, comment="Original PnL reported by broker")
    broker_commission = Column(Numeric(18, 2), nullable=True, comment="Original commission reported by broker")
    broker_swap = Column(Numeric(18, 2), nullable=True, comment="Original swap reported by broker")
    reconciled_at = Column(DateTime(timezone=True), nullable=True, comment="Last successful broker reconciliation")
    reconciliation_status = Column(String(20), default="PENDING", comment="PENDING, SUCCESS, FAILED")

    # Additional Metadata (Confluence zones, indicators, etc.)
    metadata_json = Column(JSONB, nullable=True,
                          comment="Additional trade metadata (confluence zones, indicators, etc.)")
    
    # Phase 9: Knowledge-Driven Intelligence
    knowledge_context = Column(JSONB, nullable=True,
                              comment="GraphRAG context snapshot from FalkorDB")
    knowledge_score = Column(Numeric(5, 4), nullable=True,
                           comment="Semantic confidence score (0.0 to 1.5)")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                       comment="Record creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                       onupdate=func.now(),
                       comment="Record last update timestamp")

    # [PHASE 12] RBAC & Institutional Tracking
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True,
                     comment="Owner of the trade (RBAC)")
    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id"), nullable=True, index=True,
                     comment="Fund that the trade belongs to (RBAC)")
    latency_ms = Column(Numeric(10, 4), nullable=True,
                        comment="Total systemic latency (Signal -> Execution Fill)")

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


class PostMortem(Base):
    __tablename__ = "post_mortems"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trade_id = Column(UUID(as_uuid=True), ForeignKey("trades.trade_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    summary = Column(Text, nullable=True)
    classification = Column(String(50), nullable=True, comment="GOOD_WIN, BAD_WIN, GOOD_LOSS, BAD_LOSS")
    execution_quality = Column(Text, nullable=True)
    psychological_analysis = Column(Text, nullable=True)
    alpha_lesson = Column(Text, nullable=True)
    
    # Metrics
    slippage_pips = Column(Float, nullable=True)
    execution_latency_ms = Column(Float, nullable=True)
    profit_efficiency = Column(Float, nullable=True)
    
    # [PHASE 28] AI Institutional Hardening
    pnl_net = Column(Numeric(10, 2), nullable=True, comment="Net profit after fees and slippage")
    smart_score = Column(Integer, nullable=True, comment="Proprietary AI score for trade quality (0-100)")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
