"""
Candle SQLAlchemy model.
Source of truth: specs/03_data_model.yaml -> Candle entity
"""

from sqlalchemy import Column, String, DateTime, Numeric, Index, func, Boolean, ForeignKey, Uuid
from sqlalchemy.dialects.postgresql import JSONB
import uuid
from app.database import Base


class Candle(Base):
    __tablename__ = "candles"
    __table_args__ = {"extend_existing": True}

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Core Identification
    market_symbol_id = Column(Uuid(as_uuid=True), ForeignKey("market_symbols.id", ondelete="CASCADE"), nullable=False, index=True,
                             comment="Foreign Key to MarketSymbol (defines Symbol + DataSource)")
    
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
    
    # Dynamic Indicators (JSONB)
    indicators = Column(JSONB, nullable=True, comment="Flexible storage for calculated indicators (RSI, EMA, etc.)")

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                       comment="Record creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
                       comment="Record last update timestamp")

    # Indexes for performance
    __table_args__ = (
        Index('ix_candles_market_symbol_timeframe_timestamp', 'market_symbol_id', 'timeframe', 'timestamp', unique=True),
        {
            'comment': 'OHLCV candlestick data with multi-timeframe indicators',
            'extend_existing': True
        }
    )

    def __repr__(self):
        return f"<Candle {self.market_symbol_id} {self.timeframe} {self.timestamp} close={self.close}>"
