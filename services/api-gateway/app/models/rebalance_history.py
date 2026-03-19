from sqlalchemy import Column, String, DateTime, Float, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class RebalanceHistory(Base):
    __tablename__ = "rebalance_history"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id"), nullable=False, index=True)

    trigger_type = Column(String(30), nullable=False)  # MANUAL | AUTONOMOUS | SENTIMENT_DRIFT
    drift_score = Column(Float, nullable=True)
    previous_config = Column(JSONB, nullable=False)
    applied_config = Column(JSONB, nullable=False)
    reasoning = Column(Text, nullable=False)
    applied_by = Column(String(100), nullable=False)  # user_id or "SYSTEM"

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    fund = relationship("Fund", back_populates="rebalance_history")
