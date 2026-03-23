from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.database import Base

class UserRole(str, enum.Enum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    TRADER = "TRADER"
    VIEWER = "VIEWER"



class Fund(Base):
    __tablename__ = "funds"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Risk Settings (Advanced Risk Parameters)
    strategy_type = Column(Enum("MTF_SMC_BASIC", "LONG_SHORT_EQUITY", "MACRO_TACTICAL", "MULTI_ASSET", name="strategy_type_enum"), default="MTF_SMC_BASIC", nullable=False)
    asset_classes = Column(JSONB, default=["FX"], nullable=False)
    max_risk_per_trade = Column(Numeric(10, 2), default=10.0, nullable=False)
    risk_percentage = Column(Numeric(5, 4), default=0.01) # Default 1%
    default_lot_size = Column(Numeric(10, 2), default=0.01, nullable=False)
    max_drawdown_threshold = Column(Numeric(10, 2), nullable=True)
    max_portfolio_beta = Column(Numeric(5, 2), default=0.35, nullable=True)
    gross_exposure_limit = Column(Numeric(5, 2), default=100.0, nullable=True)
    net_exposure_limit = Column(Numeric(5, 2), default=15.0, nullable=True)
    position_limit_single = Column(Numeric(5, 2), default=3.0, nullable=True)
    position_limit_sector = Column(Numeric(5, 2), default=10.0, nullable=True)

    risk_parity_enabled = Column(Boolean, default=False)
    risk_parity_model = Column(Enum("MIN_VOL", "HRP", "ERC", name="risk_parity_model_enum"), default="HRP")
    scale_factor = Column(Numeric(5, 4), default=1.0000, nullable=False)
    asset_risk_caps = Column(JSONB, default={}, nullable=False)

    # [NEW] Auto-Protect (Emergency SL)
    auto_protect_enabled = Column(Boolean, default=False, nullable=False)
    emergency_sl_pips = Column(Numeric(10, 2), default=500.0, nullable=False)

    # Relationships
    users = relationship("UserFund", back_populates="fund", cascade="all, delete-orphan")
    broker_accounts = relationship("BrokerAccount", back_populates="fund", cascade="all, delete-orphan")
    strategies = relationship("Strategy", back_populates="fund", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="fund", cascade="all, delete-orphan")
    allocations = relationship("PortfolioAllocation", back_populates="fund", cascade="all, delete-orphan")
    rebalance_history = relationship("RebalanceHistory", back_populates="fund", cascade="all, delete-orphan")

class UserFund(Base):
    __tablename__ = "user_funds"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id"), nullable=False)
    role = Column(Enum(UserRole), nullable=False)

    user = relationship("User", back_populates="funds")
    fund = relationship("Fund", back_populates="users")
