from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Integer, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime
from app.database import Base

class SignalLog(Base):
    """
    Persisted log of signals detected by strategies (both scanner and custom deployments).
    """
    __tablename__ = "signal_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    symbol = Column(String, nullable=False, index=True)
    timeframe = Column(String, default="H1")
    direction = Column(String, nullable=False) # BULLISH, BEARISH, NEUTRAL
    
    strategy_name = Column(String, nullable=True) # "SMC Scanner" or "Deployment-123"
    deployment_id = Column(UUID(as_uuid=True), ForeignKey("deployments.id"), nullable=True, index=True)
    
    confidence = Column(Numeric(5, 4), default=0.0)
    price = Column(Float, nullable=True) # Price at signal detection
    reason = Column(String, nullable=True)
    
    meta_data = Column(JSONB, nullable=True) # Extra info (SL/TP suggestions, indicators)

    # Relationships
    deployment = relationship("Deployment", backref="signals")
