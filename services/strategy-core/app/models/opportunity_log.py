from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Integer, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime
from app.database import Base

class OpportunityLog(Base):
    """
    Log of trade opportunities that were skipped due to filtering logic (e.g. Volatility Filter).
    """
    __tablename__ = "opportunity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    symbol = Column(String, nullable=False, index=True)
    timeframe = Column(String, default="H1")
    direction = Column(String, nullable=False) # BULLISH, BEARISH
    
    strategy_name = Column(String, nullable=True) # Strategy that identified the setup
    
    # Filter Details
    filter_name = Column(String, nullable=False) # e.g., "ATR_VOLATILITY", "SENTIMENT", "VOLUME_PROFILE"
    filter_value = Column(Float, nullable=True) # The value that triggered the filter (e.g. ATR=0.5)
    threshold_value = Column(Float, nullable=True) # The threshold used (e.g. Min ATR=1.0)
    
    reason = Column(String, nullable=True) # Detailed reason
    meta_data = Column(JSONB, nullable=True) # Indicators snapshot
