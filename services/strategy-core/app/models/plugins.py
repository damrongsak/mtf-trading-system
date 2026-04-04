from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from ..database import Base

class PluginCategory(str, enum.Enum):
    ALPHA = "ALPHA"
    RISK = "RISK"
    EXECUTION = "EXECUTION"
    UTILITY = "UTILITY"

class Plugin(Base):
    __tablename__ = "plugins"

    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    author = Column(String(100), nullable=True)
    version = Column(String(50), nullable=False)
    category = Column(Enum(PluginCategory, name="plugin_category"), nullable=False)
    base_config_schema = Column(JSONB, nullable=False, default={})
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user_installations = relationship("UserPlugin", back_populates="plugin")

class UserPlugin(Base):
    __tablename__ = "user_plugins"

    instance_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    plugin_id = Column(String(100), ForeignKey("plugins.id"), nullable=False)
    is_active = Column(Boolean, default=False)
    config_overrides = Column(JSONB, nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="plugins")
    plugin = relationship("Plugin", back_populates="user_installations")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=True)
    details_json = Column(JSONB, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
