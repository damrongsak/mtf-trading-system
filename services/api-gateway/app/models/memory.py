from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy.sql import func
import uuid
from app.database import Base

class EpisodicMemory(Base):
    """
    Persistent AI 'lessons learned' and episodic context.
    Strictly isolated by user_id for RBAC compliance.
    """
    __tablename__ = "memories"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id"), nullable=True, index=True)
    
    symbol = Column(String(20), nullable=True, index=True)
    timeframe = Column(String(10), nullable=True)
    intent = Column(String(50), nullable=True) # e.g. STRATEGY_EXPLAIN, MARKET_ANALYSIS
    
    content = Column(Text, nullable=False)
    embedding = Column(Vector(3072), nullable=True) # Gemini-embedding-001 dimension
    
    meta = Column(JSONB, default={}, server_default='{}')
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
