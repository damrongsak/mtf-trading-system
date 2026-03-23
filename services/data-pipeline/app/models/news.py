from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base

class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True)
    external_id = Column(String, unique=True, index=True, nullable=False) # Hash of URL
    
    title = Column(String, nullable=False)
    source = Column(String, nullable=False)
    url = Column(String, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    symbol = Column(String, index=True, nullable=True)
    category = Column(String, nullable=True) # e.g. Geopolitics, Fed Policy
    relevance_score = Column(Integer, default=0)
    impact_rationale = Column(String, nullable=True) # The "Why"
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
