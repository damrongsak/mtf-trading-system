from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, JSON, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.database import Base
import enum

class GameLevel(str, enum.Enum):
    A_GAME = "A_GAME"
    B_GAME = "B_GAME"
    C_GAME = "C_GAME"

class JournalEntry(Base):
    __tablename__ = "journal_entries"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    trade_id = Column(UUID(as_uuid=True), nullable=True, unique=True, index=True) # Link to source trade
    
    # Technical Context
    symbol = Column(String, nullable=False) # e.g., XAU/USD
    direction = Column(String, nullable=False) # LONG / SHORT
    entry_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    pnl_amount = Column(Float, nullable=True)
    pnl_r = Column(Float, nullable=True) # R-Multiple
    
    # Risk Management
    risk_amount = Column(Float, nullable=True)
    stop_loss_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)
    
    # Context
    session = Column(String, nullable=True) # Asian, London, NY
    context_score = Column(Integer, nullable=True) # 1-10
    
    # Game Level
    game_level = Column(Enum(GameLevel), nullable=True)
    
    # AI Episodic Memory
    is_ai_generated = Column(Boolean, default=False, nullable=False)
    ai_insight = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="journal_entries")
    mental_state = relationship("MentalState", uselist=False, back_populates="journal_entry", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="journal_entry", cascade="all, delete-orphan")
    root_cause = relationship("RootCauseAnalysis", uselist=False, back_populates="journal_entry", cascade="all, delete-orphan")

class MentalState(Base):
    __tablename__ = "mental_states"
    __table_args__ = {"extend_existing": True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journal_entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False)
    
    # Severity Levels (1-10)
    greed_level = Column(Integer, default=0)
    fear_level = Column(Integer, default=0)
    tilt_level = Column(Integer, default=0)
    confidence_level = Column(Integer, default=0)
    discipline_level = Column(Integer, default=0)
    
    journal_entry = relationship("JournalEntry", back_populates="mental_state")

class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    __table_args__ = {"extend_existing": True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journal_entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False)
    
    type = Column(String, nullable=False) # TRIGGER, THOUGHT, EMOTION, BEHAVIOR
    description = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    order_index = Column(Integer, nullable=False)
    
    journal_entry = relationship("JournalEntry", back_populates="timeline_events")

class RootCauseAnalysis(Base):
    __tablename__ = "root_cause_analyses"
    __table_args__ = {"extend_existing": True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journal_entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False)
    
    problem = Column(Text, nullable=True)
    why_exist = Column(Text, nullable=True)
    flaw = Column(Text, nullable=True)
    correction = Column(Text, nullable=True)
    logic = Column(Text, nullable=True)
    
    journal_entry = relationship("JournalEntry", back_populates="root_cause")

