from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.database import Base

class DecisionLog(Base):
    __tablename__ = "decision_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    component = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)
    prompt_version = Column(String, nullable=True) # e.g., "v1.0"
    tool_call = Column(JSON, nullable=True) # Details of action
    outcome = Column(JSON, nullable=True) # Result/Feedback
