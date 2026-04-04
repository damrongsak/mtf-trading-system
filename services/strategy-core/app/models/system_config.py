"""
System Configuration Model
Source of truth for global dynamic settings (e.g., Supported Timeframes).
"""

from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.database import Base

class SystemConfig(Base):
    __tablename__ = "system_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(50), unique=True, nullable=False, index=True, comment="Config key (e.g. 'supported_timeframes')")
    value = Column(JSONB, nullable=False, comment="Config value (JSON)")
    description = Column(String(200), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<SystemConfig {self.key}={self.value}>"
