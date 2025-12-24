from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, text
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
    broker_account_id = Column(UUID(as_uuid=True), ForeignKey("broker_accounts.id"), nullable=True) # Check specs if nullable. Specs say required, but existing data? Let's assume nullable for migration then required later. Spec says required=true. But to migrate safely, we might need default or allow null first. Let's stick to specs: nullable=False ideally but might break existing. I will make it nullable=True for now to avoid migration breakage unless I can provide default. Existing rows have no broker_account. I'll make it nullable=True.
    template_id = Column(String, nullable=False, comment="Identifier for the strategy logic template (e.g., 'SMC_V1')") # Was 'type'
    config_json = Column(JSONB, nullable=False, comment="Strategy-specific configuration parameters (overrides template defaults)")
    risk_settings = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    custom_code = Column(String, nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=text("now()"))
    updated_at = Column(DateTime, server_default=text("now()"), onupdate=text("now()"))
    # Relationships
    fund = relationship("Fund", back_populates="strategies")
    broker_account = relationship("BrokerAccount")
