from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base

class BacktestConfig(Base):
    __tablename__ = "backtest_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True) # Future multi-tenancy
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    
    # Stores the BacktestRequest payload (symbol, timeframe, dates, strategy_params, optimization_config)
    config_json = Column(JSONB, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    runs = relationship("BacktestHistory", back_populates="config")

class BacktestHistory(Base):
    __tablename__ = "backtest_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_id = Column(UUID(as_uuid=True), ForeignKey("backtest_configs.id"), nullable=True)
    strategy_id = Column(UUID(as_uuid=True), nullable=True) # Optional direct link
    
    # Snapshot of the config used for this specific run (in case config changed later)
    execution_config = Column(JSONB, nullable=False)
    
    # Results
    status = Column(String(20), default="COMPLETED") # COMPLETED, FAILED, RUNNING
    metrics = Column(JSONB, nullable=True) # Total Return, Sharpe, Win Rate...
    best_params = Column(JSONB, nullable=True) # If optimization was run
    
    # Storage for large result sets could be external (S3), but for MVP we store summary here
    # equity_curve = Column(JSONB, nullable=True) # Potentially large, be careful
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    config = relationship("BacktestConfig", back_populates="runs")
