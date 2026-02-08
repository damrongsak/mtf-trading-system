from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.sql import func
from app.database import Base

class EconomicEvent(Base):
    __tablename__ = "economic_events"

    id = Column(Integer, primary_key=True, index=True)
    # Composite unique key conceptual, but we'll use a generated external_id or hash for dedupe
    external_id = Column(String, unique=True, index=True, nullable=True) 
    
    title = Column(String, nullable=False)
    country = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    impact = Column(String, nullable=False) # High, Medium, Low
    
    datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    
    actual = Column(String, nullable=True) 
    forecast = Column(String, nullable=True)
    previous = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
