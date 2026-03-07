from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base
import uuid

class StrategyExecutionLog(Base):
    """
    Stores resource-efficient logs of strategy calculations (reasoning, signals).
    Captures essential outputs only to minimize storage impact.
    """
    __tablename__ = "strategy_execution_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_id = Column(UUID(as_uuid=True), ForeignKey("deployments.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Store essential output: { "reasoning": "...", "signals": [...], "indicators": {...} }
    essential_output = Column(JSONB, nullable=False)

    def __repr__(self):
        return f"<StrategyExecutionLog(deployment={self.deployment_id}, time={self.timestamp})>"
