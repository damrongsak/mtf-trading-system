
from sqlalchemy import Column, String, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base
import uuid

class SavedStrategy(Base):
    __tablename__ = "saved_strategies"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(Text, nullable=False)
    parameters = Column(JSONB, nullable=False, default={})
    is_public = Column(Boolean, default=False)
