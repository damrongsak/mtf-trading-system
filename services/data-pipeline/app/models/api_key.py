from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer, Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.database import Base

class ApiKeyRole(str, enum.Enum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    TRADER = "TRADER"
    VIEWER = "VIEWER"

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id"), nullable=True)
    name = Column(String(100), nullable=False)
    api_key = Column(String(100), unique=True, nullable=False, index=True)
    api_secret = Column(String, nullable=False) # Encrypted string
    
    role = Column(SqlEnum(ApiKeyRole), default=ApiKeyRole.VIEWER, nullable=False)
    scopes = Column(JSONB, server_default='["*"]', nullable=False)
    allowed_ips = Column(JSONB, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    rate_limit_rpm = Column(Integer, server_default='60', nullable=False)
    
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="api_keys")
    fund = relationship("Fund")
