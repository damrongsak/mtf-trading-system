"""
Candle SQLAlchemy model.
"""

from sqlalchemy import Column, String, DateTime, Numeric, Index, func, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.database import Base


class Candle(Base):
    """
    OHLCV candlestick data with multi-timeframe indicators.
    """
    __tablename__ = "candles"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Core Identification
    symbol = Column(String(20), nullable=False, index=True,
                   comment="Trading pair symbol (e.g., XAU/USD)")
    timeframe = Column(String(10), nullable=False, index=True,
                      comment="Timeframe identifier (15m, 1h, 4h, D)")
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True,
                      comment="Candle open timestamp (UTC)")

    # OHLCV Data
    open = Column(Numeric(18, 8), nullable=False,
                 comment="Opening price")
    high = Column(Numeric(18, 8), nullable=False,
                 comment="Highest price")
    low = Column(Numeric(18, 8), nullable=False,
                comment="Lowest price")
    close = Column(Numeric(18, 8), nullable=False,
                  comment="Closing price")
    volume = Column(Numeric(18, 8), nullable=False,
                   comment="Trading volume")
    is_complete = Column(Boolean, default=True, comment="Whether the candle is closed/complete")

    # Multi-Timeframe Indicators (Non-Look-Ahead)
    ema_9_4h = Column(Numeric(18, 8), nullable=True,
                     comment="EMA(9) on 4H timeframe (for 15m candles, aligned)")
    ema_200_4h = Column(Numeric(18, 8), nullable=True,
                       comment="EMA(200) on 4H timeframe (macro bias filter)")
    ema_200_d = Column(Numeric(18, 8), nullable=True,
                      comment="EMA(200) on Daily timeframe (macro bias filter)")
    atr_14_15m = Column(Numeric(18, 8), nullable=True,
                       comment="ATR(14) on 15m timeframe (for stop loss calculation)")
    body_to_wick_ratio = Column(Numeric(5, 4), nullable=True,
                               comment="Body-to-Wick Ratio (Rv) for vector candle confirmation")

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                       comment="Record creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
                       comment="Record last update timestamp")

    # Indexes for performance
    __table_args__ = (
        Index('ix_candles_symbol_timeframe_timestamp', 'symbol', 'timeframe', 'timestamp', unique=True),
        {'comment': 'OHLCV candlestick data with multi-timeframe indicators'}
    )

    def __repr__(self):
        return f"<Candle {self.symbol} {self.timeframe} {self.timestamp} close={self.close}>"
