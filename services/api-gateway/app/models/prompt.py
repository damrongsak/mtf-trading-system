import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class SystemPrompt(Base):
    __tablename__ = "system_prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    template = Column(Text, nullable=False)
    input_variables = Column(JSON, default=list) # List of strings e.g. ["market_data", "user_query"]
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", backref="prompts")

    def to_dict(self):
        return {
            "id": str(self.id),
            "owner_id": str(self.owner_id),
            "name": self.name,
            "description": self.description,
            "template": self.template,
            "input_variables": self.input_variables,
            "version": self.version,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False) # CREATE, UPDATE, DELETE
    resource_type = Column(String, nullable=False) # PROMPT, AGENT
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    changes = Column(JSON, nullable=True) # Diff or details
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
