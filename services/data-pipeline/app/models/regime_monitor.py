from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, JSON, text, Index
from app.database import Base

class RegimeMonitor(Base):
    __tablename__ = "regime_monitor"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    gex_proxy = Column(Numeric(20, 4), nullable=False)
    underlying_price = Column(Numeric(18, 8), nullable=True)
    regime_type = Column(String(50), nullable=False)
    fragility_index = Column(Numeric(10, 4), nullable=True)
    is_valid = Column(Boolean, server_default='true', nullable=False)
    is_noise = Column(Boolean, server_default='false', nullable=False)
    meta_data = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text('now()'), nullable=False)

    __table_args__ = (
        Index('ix_regime_monitor_symbol_timestamp', 'symbol', 'timestamp', unique=True),
    )
