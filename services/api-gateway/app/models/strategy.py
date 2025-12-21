from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
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
    type = Column(String, nullable=False, comment="Strategy class/type identifier")
    config_json = Column(JSONB, nullable=False, comment="Strategy-specific configuration parameters")
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    fund = relationship("Fund", back_populates="strategies")
