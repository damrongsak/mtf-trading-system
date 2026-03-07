from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base

class MentalHandHistory(Base):
    __tablename__ = "mental_hand_histories"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    journal_entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True)
    
    pre_trade_emotion = Column(String(50))
    trigger_event = Column(String)
    irrational_thought = Column(Text)
    behavioral_result = Column(Text)
    correction_logic = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="mental_hand_histories")
    journal_entry = relationship("JournalEntry")
