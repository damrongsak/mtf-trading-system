from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base

class StrategyConfig(Base):
    __tablename__ = "strategy_configs"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    logic_schema_version = Column(String, default="1.0.0")
    logic_blocks = Column(JSONB, nullable=False)
    parameters = Column(JSONB, nullable=False)
    timeframe_settings = Column(JSONB, nullable=False)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    author = relationship("User", back_populates="strategy_configs")
    validations = relationship("StrategyValidation", back_populates="config")
    # strategies = relationship("Strategy", back_populates="config") # Added to strategy.py

class StrategyValidation(Base):
    __tablename__ = "strategy_validations"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_id = Column(UUID(as_uuid=True), ForeignKey("strategy_configs.id"), nullable=False)
    robustness_score = Column(Integer, nullable=False)
    
    # Train Metrics
    sharpe_train = Column(Numeric(5, 2))
    car_train = Column(Numeric(5, 2))
    max_dd_train = Column(Numeric(5, 2))
    
    # Test Metrics
    sharpe_test = Column(Numeric(5, 2))
    car_test = Column(Numeric(5, 2))
    max_dd_test = Column(Numeric(5, 2))
    
    validation_date = Column(DateTime(timezone=True), server_default=func.now())
    is_passed = Column(Boolean, default=False)

    # Relationships
    config = relationship("StrategyConfig", back_populates="validations")
