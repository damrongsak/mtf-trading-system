
from sqlalchemy import Column, String, Boolean, DateTime, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import uuid

class Deployment(Base):
    __tablename__ = "deployments"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    strategy_id = Column(UUID(as_uuid=True), nullable=False)
    
    stock_symbol = Column(String, nullable=False)
    timeframe = Column(String, nullable=False)
    config_snapshot = Column(JSON, nullable=False)
    
    status = Column(String, default="ACTIVE")
    is_live = Column(Boolean, default=False)
    
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    last_signal_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(String, nullable=True)
