
from sqlalchemy import Column, String, DateTime, Numeric, Integer, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.database import Base
from sqlalchemy.sql import func
import enum

class TradeStatus(enum.Enum):
    """Trade execution status"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"

class TradeDirection(enum.Enum):
    """Trade direction"""
    LONG = "LONG"
    SHORT = "SHORT"

class BrokerAccount(Base):
    __tablename__ = "broker_accounts"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_id = Column(UUID(as_uuid=True), nullable=False)
    broker_name = Column(String(50), nullable=False)
    account_number = Column(String(50), nullable=True)
    credentials_encrypted = Column(JSONB, nullable=False) # Encrypted credentials as JSON
    environment = Column(String(20), default="demo")
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = {"extend_existing": True}

    trade_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # broker_account_id is a foreign key, but we might not enforce it if we want loose coupling
    # But for now, we replicate it.
    broker_account_id = Column(UUID(as_uuid=True), ForeignKey("broker_accounts.id"), nullable=True, index=True)
    
    symbol = Column(String(20), nullable=False, index=True)
    strategy_name = Column(String(100), nullable=False)
    signal_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    status = Column(String(20), nullable=False, index=True) # Using String for simplicity in pipeline, or Enum if we share
    # We'll use the Enum values but store as String or Enum. Let's match API Gateway exactly if possible.
    # API Gateway uses SQLEnum(TradeStatus). To avoid importing Enum issues, we can use String or define Enum.
    # Defined above.

    rejection_reason = Column(String(500), nullable=True)

    direction = Column(String(10), nullable=False) # LONG/SHORT
    entry_price = Column(Numeric(18, 8), nullable=False)
    sl_price = Column(Numeric(18, 8), nullable=False)
    tp_price = Column(Numeric(18, 8), nullable=False)

    lot_size = Column(Numeric(12, 6), nullable=False)
    risk_usd = Column(Numeric(10, 2), nullable=False)
    pnl_usd = Column(Numeric(10, 2), nullable=True)
    
    # Enhanced Data Fields
    commission = Column(Numeric(10, 2), nullable=True)
    swap = Column(Numeric(10, 2), nullable=True)
    gross_pnl = Column(Numeric(10, 2), nullable=True)
    
    broker_trade_id = Column(String(100), nullable=True, index=True) # Position ID or equivalent
    broker_deal_id = Column(String(100), nullable=True, unique=True) # Deal ID / Transaction ID

    
    exit_price = Column(Numeric(18, 8), nullable=True)
    exit_timestamp = Column(DateTime(timezone=True), nullable=True)

    metadata_json = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
