"""
Trade SQLAlchemy model (AI-Analyst Subset).
Source of truth: specs/03_data_model.yaml -> Trade entity
"""

from sqlalchemy import Column, String, DateTime, Numeric, Integer, Enum as SQLEnum, Index, func, Text, Boolean, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import enum
from app.database import Base


class TradeStatus(enum.Enum):
    OPEN = "OPEN"
    PENDING = "PENDING"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"


class TradeDirection(enum.Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = {"extend_existing": True}

    trade_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_run_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    broker_account_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    broker_trade_id = Column(String(100), nullable=True, index=True)
    
    symbol = Column(String(20), nullable=False, index=True)
    strategy_name = Column(String(100), nullable=False)
    signal_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    status = Column(SQLEnum(TradeStatus), nullable=False, index=True)
    direction = Column(SQLEnum(TradeDirection), nullable=False)
    
    entry_price = Column(Numeric(18, 8), nullable=False)
    exit_price = Column(Numeric(18, 8), nullable=True)
    exit_timestamp = Column(DateTime(timezone=True), nullable=True)
    pnl_usd = Column(Numeric(10, 2), nullable=True)
    
    metadata_json = Column(JSONB, nullable=True)
    
    # Phase 9: Knowledge-Driven Intelligence
    knowledge_context = Column(JSONB, nullable=True)
    knowledge_score = Column(Numeric(5, 4), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Trade {self.trade_id} {self.symbol} {self.direction.value} {self.status.value}>"
