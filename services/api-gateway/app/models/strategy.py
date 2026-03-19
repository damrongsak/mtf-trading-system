from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base

class Strategy(Base):
    __tablename__ = "strategies"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id"), nullable=False)
    name = Column(String(100), nullable=False)
    broker_account_id = Column(UUID(as_uuid=True), ForeignKey("broker_accounts.id"), nullable=False)
    
    # Olympus: Strategy Config Link
    config_id = Column(UUID(as_uuid=True), ForeignKey("strategy_configs.id"), nullable=True)

    template_id = Column(String, nullable=False, comment="Identifier for the strategy logic template (e.g., 'SMC_V1')") # Was 'type'
    config_json = Column(JSONB, nullable=False, comment="Strategy-specific configuration parameters (overrides template defaults)")
    risk_settings = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    custom_code = Column(String, nullable=True)
    is_active = Column(Boolean, default=False)
    is_shadow = Column(Boolean, default=False, comment="If true, signals are processed fully but not sent to the broker")
    
    # Persistence Fields
    last_backtest_result = Column(JSONB, nullable=True)
    last_optimization_result = Column(JSONB, nullable=True)
    last_simulation_result = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, server_default=text("now()"))
    updated_at = Column(DateTime, server_default=text("now()"), onupdate=text("now()"))
    # Relationships
    fund = relationship("Fund", back_populates="strategies")
    broker_account = relationship("BrokerAccount")
    config = relationship("StrategyConfig")
    allocations = relationship("PortfolioAllocation", back_populates="strategy", cascade="all, delete-orphan")
