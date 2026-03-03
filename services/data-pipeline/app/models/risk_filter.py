"""
Risk Filter Model
Hierarchical Risk Management filters (System, Fund, BrokerAccount, Strategy)
"""

from sqlalchemy import Column, String, DateTime, Boolean, Enum, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import enum
from app.database import Base

class TargetType(str, enum.Enum):
    SYSTEM = "SYSTEM"
    FUND = "FUND"
    BROKER_ACCOUNT = "BROKER_ACCOUNT"
    STRATEGY = "STRATEGY"

class RiskFilter(Base):
    __tablename__ = "risk_filters"
    __table_args__ = (
        UniqueConstraint('target_type', 'target_id', 'filter_type', name='uq_risk_filter_target_type_id'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_type = Column(Enum(TargetType, name="target_type_enum"), nullable=False, index=True)
    target_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    filter_type = Column(String(50), nullable=False, index=True)
    is_enabled = Column(Boolean, default=True)
    threshold_parameters = Column(JSONB, nullable=False, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<RiskFilter {self.target_type}={self.target_id} {self.filter_type}>"
