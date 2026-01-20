import uuid
from sqlalchemy import Column, String, JSON, Numeric, Boolean, Integer, ForeignKey, DateTime, Enum as SQLEnum, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum
from app.database import Base

class TradeStatus(enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"

class TradeDirection(enum.Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class BrokerAccount(Base):
    __tablename__ = "broker_accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    fund_id = Column(UUID(as_uuid=True), nullable=False) # ForeignKey not enforced in execution app models usually unless imported, but field MUST exist
    
    broker_name = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    account_number = Column(String, nullable=True)
    
    credentials_encrypted = Column(JSONB, nullable=False) # Maps to jsonb in DB
    is_active = Column(Boolean, default=True)
    is_live = Column(Boolean, default=False)
    environment = Column(String, default="practice", nullable=False) # New column
    
    supported_symbols = Column(JSONB, nullable=True)
    risk_settings = Column(JSONB, nullable=True)
    
class Fund(Base):
    __tablename__ = "funds"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    strategy_type = Column(String, nullable=False) 
    max_risk_per_trade = Column(Numeric(10, 2), nullable=False)
    risk_percentage = Column(Numeric(5, 4), default=0.01) 
    asset_classes = Column(JSON, nullable=False) # execution app uses JSON for this
    default_lot_size = Column(Numeric(10, 2), nullable=False)
    max_drawdown_threshold = Column(Numeric(10, 2), nullable=True)

class MarketCategory(Base):
    __tablename__ = "market_categories"

    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False, index=True)
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # items = relationship("MarketSymbol", back_populates="category") # Avoid backref issues if not needed

class DataSource(Base):
    __tablename__ = "data_sources"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    provider = Column(String, nullable=True) 
    type = Column(String, nullable=False)
    config_json = Column(JSONB, nullable=False)
    schema_json = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True)

class MarketSymbol(Base):
    __tablename__ = "market_symbols"

    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("market_categories.id"), nullable=False)
    data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=True)
    symbol = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    details = Column(JSONB, nullable=True)
    
    data_source = relationship("DataSource")
    category = relationship("MarketCategory")

class Candle(Base):
    __tablename__ = "candles"
    
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_symbol_id = Column(UUID(as_uuid=True), ForeignKey("market_symbols.id"), nullable=False)
    
    timestamp = Column(DateTime(timezone=True), nullable=False)
    timeframe = Column(String, nullable=False)
    
    open = Column(Numeric, nullable=False)
    high = Column(Numeric, nullable=False)
    low = Column(Numeric, nullable=False)
    close = Column(Numeric, nullable=False)
    volume = Column(Numeric, nullable=False)
    
    # Use relationship if needed, or just ID
    # market_symbol = relationship("MarketSymbol")

class Trade(Base):
    __tablename__ = "trades"
    
    trade_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_run_id = Column(UUID(as_uuid=True), nullable=True)
    broker_account_id = Column(UUID(as_uuid=True), ForeignKey("broker_accounts.id"), nullable=True)
    symbol = Column(String(20), nullable=False)
    strategy_name = Column(String(100), nullable=False)
    signal_timestamp = Column(DateTime(timezone=True), nullable=False)
    
    status = Column(SQLEnum(TradeStatus, name="tradestatus"), nullable=False) # OPEN, CLOSED, REJECTED
    rejection_reason = Column(String(500), nullable=True)
    
    direction = Column(SQLEnum(TradeDirection, name="tradedirection"), nullable=False) # LONG, SHORT
    entry_price = Column(Numeric(18, 8), nullable=False)
    sl_price = Column(Numeric(18, 8), nullable=False)
    tp_price = Column(Numeric(18, 8), nullable=False)
    
    lot_size = Column(Numeric(10, 2), nullable=False)
    risk_usd = Column(Numeric(10, 2), nullable=False)
    atr_pips = Column(Numeric(10, 2), nullable=True)
    rr_ratio = Column(Numeric(5, 2), nullable=True)
    
    pnl_usd = Column(Numeric(10, 2), nullable=True)
    mae_usd = Column(Numeric(10, 2), nullable=True)
    mfe_usd = Column(Numeric(10, 2), nullable=True)
    
    exit_price = Column(Numeric(18, 8), nullable=True)
    exit_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    metadata_json = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

