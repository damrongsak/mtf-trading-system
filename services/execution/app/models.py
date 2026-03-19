import uuid
from sqlalchemy import Column, String, JSON, Numeric, Boolean, Integer, ForeignKey, DateTime, Enum as SQLEnum, func, BigInteger
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

class TargetType(str, enum.Enum):
    SYSTEM = "SYSTEM"
    FUND = "FUND"
    BROKER_ACCOUNT = "BROKER_ACCOUNT"
    STRATEGY = "STRATEGY"

class RiskFilter(Base):
    __tablename__ = "risk_filters"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_type = Column(SQLEnum(TargetType, name="target_type_enum"), nullable=False, index=True)
    target_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    filter_type = Column(String(50), nullable=False, index=True)
    is_enabled = Column(Boolean, default=True)
    threshold_parameters = Column(JSONB, nullable=False, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

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
    
    # [NEW] Phase 28 Fields
    leverage = Column(Integer, default=30, nullable=True)
    currency = Column(String(10), default="USD", nullable=True)
    balance_snapshot = Column(Numeric(18, 2), nullable=True)
    data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=True)

class AccountHistory(Base):
    __tablename__ = "account_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    broker_account_id = Column(UUID(as_uuid=True), ForeignKey("broker_accounts.id"), nullable=False, index=True)
    
    balance = Column(Numeric(18, 2), nullable=False)
    equity = Column(Numeric(18, 2), nullable=False)
    used_margin = Column(Numeric(18, 2), nullable=False)
    free_margin = Column(Numeric(18, 2), nullable=False)
    margin_level = Column(Numeric(10, 2), nullable=True)
    unrealized_gross = Column(Numeric(18, 2), nullable=True)
    unrealized_net = Column(Numeric(18, 2), nullable=True)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
class Fund(Base):
    __tablename__ = "funds"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    strategy_type = Column(String, nullable=False) 
    max_risk_per_trade = Column(Numeric(10, 2), nullable=False)
    risk_percentage = Column(Numeric(5, 4), default=0.01) 
    asset_classes = Column(JSON, nullable=False) # execution app uses JSON for this
    default_lot_size = Column(Numeric(10, 2), nullable=False)
    max_drawdown_threshold = Column(Numeric(10, 2), nullable=True)

    risk_parity_enabled = Column(Boolean, default=False)
    risk_parity_model = Column(SQLEnum("MIN_VOL", "HRP", "ERC", name="risk_parity_model_enum"), default="HRP")

class MarketCategory(Base):
    __tablename__ = "market_categories"

    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    is_live = Column(Boolean, default=False)
    is_shadow = Column(Boolean, default=False, nullable=True, comment="If true, signals are not sent to the broker")
    status = Column(SQLEnum(TradeStatus), nullable=False, index=True)
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
    broker_trade_id = Column(String(100), nullable=True)
    broker_deal_id = Column(String(100), nullable=True, unique=True)
    symbol = Column(String(20), nullable=False)
    strategy_name = Column(String(100), nullable=False)
    signal_timestamp = Column(DateTime(timezone=True), nullable=False)
    signal_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    is_shadow = Column(Boolean, default=False, nullable=True)
    signal_timestamp_ns = Column(BigInteger, nullable=True)
    latency_ms = Column(Numeric(10, 4), nullable=True)
    
    status = Column(SQLEnum(TradeStatus, name="tradestatus"), nullable=False) # OPEN, CLOSED, REJECTED
    rejection_reason = Column(String(500), nullable=True)
    
    direction = Column(SQLEnum(TradeDirection, name="tradedirection"), nullable=False) # LONG, SHORT
    entry_price = Column(Numeric(18, 8), nullable=False)
    sl_price = Column(Numeric(18, 8), nullable=False)
    tp_price = Column(Numeric(18, 8), nullable=False)
    trailing_stop = Column(Boolean, default=False, nullable=True)
    
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

class EconomicEvent(Base):
    __tablename__ = "economic_events"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True, nullable=True) 
    title = Column(String, nullable=False)
    country = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    impact = Column(String, nullable=False) # High, Medium, Low
    datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    actual = Column(String, nullable=True) 
    forecast = Column(String, nullable=True)
    previous = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class NewsArticle(Base):
    __tablename__ = "news_articles"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String, unique=True, index=True, nullable=True)
    symbol = Column(String, nullable=True, index=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=True)
    source = Column(String, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    sentiment_score = Column(Numeric(5, 4), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True)
    is_active = Column(Boolean, default=True)

class UserPreferences(Base):
    __tablename__ = "user_preferences"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    oanda_janitor_enabled = Column(Boolean, default=False, nullable=False)
    ctrader_janitor_enabled = Column(Boolean, default=False, nullable=False)

class Deployment(Base):
    __tablename__ = "deployments"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id"), nullable=False, index=True)
    strategy_id = Column(UUID(as_uuid=True), nullable=False)
    is_active = Column(Boolean, default=True)
    is_shadow = Column(Boolean, default=False, nullable=True, comment="If true, signals are not sent to the broker")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserFund(Base):
    __tablename__ = "user_funds"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id"), nullable=False)

class SignalLog(Base):
    __tablename__ = "signal_logs"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True)
    status = Column(String) # CREATED, PENDING_APPROVAL, EXECUTED, FILLED, REJECTED, EXPIRED, FAILED
    execution_id = Column(UUID(as_uuid=True), nullable=True)
    filled_price = Column(Numeric(18, 8), nullable=True)
    filled_time = Column(DateTime(timezone=True), nullable=True)
