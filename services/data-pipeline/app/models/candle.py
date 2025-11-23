from sqlalchemy import Column, String, DateTime, Numeric, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime

Base = declarative_base()

class Candle(Base):
    __tablename__ = "candles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    open = Column(Numeric(18, 8), nullable=False)
    high = Column(Numeric(18, 8), nullable=False)
    low = Column(Numeric(18, 8), nullable=False)
    close = Column(Numeric(18, 8), nullable=False)
    volume = Column(Numeric(18, 8), nullable=False)
    
    # MTF Indicators
    ema_9_4h = Column(Numeric(18, 8), nullable=True)
    ema_200_4h = Column(Numeric(18, 8), nullable=True)
    ema_200_d = Column(Numeric(18, 8), nullable=True)
    atr_14_15m = Column(Numeric(18, 8), nullable=True)
    body_to_wick_ratio = Column(Numeric(5, 4), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index('ix_candles_symbol_timeframe_timestamp', 'symbol', 'timeframe', 'timestamp', unique=True),
        Index('ix_candles_timestamp', 'timestamp'),
    )
