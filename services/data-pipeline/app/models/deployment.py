
from sqlalchemy import Column, String, Float, Boolean, ForeignKey, DateTime, Integer, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime # Added import for datetime

class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    fund_id = Column(UUID(as_uuid=True), ForeignKey('funds.id'), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    is_shadow = Column(Boolean, default=False, nullable=True, comment="If true, signals are not sent to the broker")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("saved_strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Configuration Snapshot
    stock_symbol = Column(String, nullable=False)
    timeframe = Column(String, nullable=False)
    config_snapshot = Column(JSONB, nullable=False)
    
    # State
    status = Column(Enum("STARTING", "ACTIVE", "STOPPED", "ERROR", "STOPPING", name="deployment_status_enum"), default="STARTING", index=True, nullable=False)
    is_live = Column(Boolean, default=False)
    
    # Performance/Tracking
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    last_signal_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="deployments")
    strategy = relationship("SavedStrategy", back_populates="deployments")
