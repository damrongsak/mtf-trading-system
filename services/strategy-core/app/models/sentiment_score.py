from sqlalchemy import Column, String, Numeric, DateTime, Integer, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.database import Base

class SentimentScore(Base):
    __tablename__ = "sentiment_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    score = Column(Numeric(5, 4), nullable=False, comment="Sentiment score (-1.0 to 1.0)")
    reason = Column(String, nullable=True)
    source_breakdown = Column(JSONB, nullable=True, comment="Sentiment source contributions")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<SentimentScore {self.symbol} score={self.score}>"
