
from sqlalchemy import Column, String, Float, Boolean, ForeignKey, DateTime, Integer, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("saved_strategies.id"), nullable=False, index=True)
    
    # Configuration Snapshot (Immutable for this deployment instance)
    stock_symbol = Column(String, nullable=False) # e.g. "XAU/USD"
    timeframe = Column(String, nullable=False)    # e.g. "M15"
    config_snapshot = Column(JSON, nullable=False) # { captial, risk_pct, strategy_params }
    
    # State
    status = Column(String, default="ACTIVE", index=True) # ACTIVE, STOPPED, ERROR
    is_live = Column(Boolean, default=False) # True = Real Money, False = Paper
    
    # Performance/Tracking
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    last_signal_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="deployments")
    strategy = relationship("SavedStrategy", back_populates="deployments")
