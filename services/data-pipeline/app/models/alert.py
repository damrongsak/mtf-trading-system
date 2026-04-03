from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Numeric, Enum as SQLEnum, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.database import Base


class AlertCondition(enum.Enum):
    """Supported alert conditions"""
    PRICE_ABOVE = "PRICE_ABOVE"
    PRICE_BELOW = "PRICE_BELOW"


class Alert(Base):
    """
    Persistent price alert model.
    Source of truth: specs/03_data_model.yaml -> Alert entity
    """
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    condition = Column(SQLEnum(AlertCondition), nullable=False)
    threshold = Column(Numeric(18, 8), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_triggered = Column(Boolean, default=False, nullable=False, index=True)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Alert {self.id} {self.symbol} {self.condition.value} {self.threshold}>"
