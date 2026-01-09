from sqlalchemy import Boolean, Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base

class User(Base):
    __tablename__ = "users"


    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    avatar_url = Column(String, nullable=True)
    reputation_score = Column(Integer, default=0)
    is_verified_quant = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    funds = relationship("UserFund", back_populates="user")
    journal_entries = relationship("JournalEntry", back_populates="user")
    mental_hand_histories = relationship("MentalHandHistory", back_populates="user")
    preferences = relationship("UserPreferences", back_populates="user", uselist=False)
    deployments = relationship("Deployment", back_populates="user")
    strategy_configs = relationship("StrategyConfig", back_populates="author")
