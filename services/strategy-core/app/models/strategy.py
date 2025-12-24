from sqlalchemy import Column, String, Boolean, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    fund_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(100), nullable=False)
    template_id = Column(String, nullable=False)
    broker_account_id = Column(UUID(as_uuid=True), nullable=False)
    config_json = Column(JSONB, nullable=False)
    risk_settings = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    custom_code = Column(String, nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=text("now()"))
    updated_at = Column(DateTime, server_default=text("now()"), onupdate=text("now()"))
