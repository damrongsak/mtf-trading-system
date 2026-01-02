from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.database import Base

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

    # No relationship backref here to avoid circular imports unless User is defined

class UserPlugin(Base):
    __tablename__ = "user_plugins"

    instance_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    plugin_id = Column(String(100), ForeignKey("plugins.id"), nullable=False)
    is_active = Column(Boolean, default=False)
    config_overrides = Column(JSONB, nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)

    # Simplified relationships for strategy-core usage
    # plugin = relationship("Plugin") 
