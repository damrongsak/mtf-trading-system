"""
Candle SQLAlchemy model (AI-Analyst Subset).
Source of truth: specs/03_data_model.yaml -> Candle entity
"""

from sqlalchemy import Column, String, DateTime, Numeric, Index, func, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.database import Base


class Candle(Base):
    __tablename__ = "candles"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Core Identification
    market_symbol_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # OHLCV Data
    open = Column(Numeric(18, 8), nullable=False)
    high = Column(Numeric(18, 8), nullable=False)
    low = Column(Numeric(18, 8), nullable=False)
    close = Column(Numeric(18, 8), nullable=False)
    volume = Column(Numeric(24, 8), nullable=False)
    is_complete = Column(Boolean, default=True)

    # Dynamic Indicators (JSONB)
    indicators = Column(JSONB, nullable=True)
    ai_labels = Column(JSONB, nullable=True)
    regime_tag = Column(String(50), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Candle {self.symbol} {self.timeframe} {self.timestamp} close={self.close}>"
