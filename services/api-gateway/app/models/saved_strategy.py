from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base

class SavedStrategy(Base):
    __tablename__ = "saved_strategies"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    code = Column(Text, nullable=False)
    parameters = Column(JSONB, nullable=False, default={})
    last_results = Column(JSONB, nullable=True, comment="Persisted backtest metrics and plot")
    last_optimization_result = Column(JSONB, nullable=True)
    last_simulation_result = Column(JSONB, nullable=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="saved_strategies")
    deployments = relationship("Deployment", back_populates="strategy")
