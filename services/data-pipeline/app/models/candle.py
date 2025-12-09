from sqlalchemy import Column, String, DateTime, Numeric, Integer, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import uuid
from datetime import datetime

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
    is_complete = Column(Boolean, default=True)
    
    # MTF Indicators
    ema_9_4h = Column(Numeric(18, 8), nullable=True)
    ema_200_4h = Column(Numeric(18, 8), nullable=True)
    ema_200_d = Column(Numeric(18, 8), nullable=True)
    atr_14_15m = Column(Numeric(18, 8), nullable=True)
    body_to_wick_ratio = Column(Numeric(5, 4), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_candles_symbol_timeframe_timestamp', 'symbol', 'timeframe', 'timestamp', unique=True),
        Index('ix_candles_timestamp', 'timestamp'),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "is_complete": self.is_complete,
            "ema_9_4h": self.ema_9_4h,
            "ema_200_4h": self.ema_200_4h,
            "ema_200_d": self.ema_200_d,
            "atr_14_15m": self.atr_14_15m,
            "body_to_wick_ratio": self.body_to_wick_ratio,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
