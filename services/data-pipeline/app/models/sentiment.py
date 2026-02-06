from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base

class SentimentScore(Base):
    __tablename__ = "sentiment_scores"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    score = Column(Float, nullable=False)
    reason = Column(String, nullable=True)
    source_breakdown = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
