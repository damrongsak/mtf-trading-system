from sqlalchemy import Column, String, Enum, DateTime, ForeignKey, Numeric, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.database import Base


class StrategyType(str, enum.Enum):
    """Strategy type enum for portfolio management"""
    MTF_SMC_BASIC = "MTF_SMC_BASIC"
    LONG_SHORT_EQUITY = "LONG_SHORT_EQUITY"
    MACRO_TACTICAL = "MACRO_TACTICAL"
    MULTI_ASSET = "MULTI_ASSET"


class UserPreferences(Base):
    __tablename__ = "user_preferences"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    
    # Fund Management
    default_fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id"), nullable=True)
    
    # Strategy Configuration
    # strategy_type moved to Fund
    # asset_classes moved to Fund
    # Risk Parameters moved to Fund
    
    # Trading Preferences
    preferred_timeframes = Column(
        JSONB, 
        default=["4H", "1H", "15m"], 
        nullable=False,
        comment="Preferred trading timeframes"
    )
    default_symbol = Column(String(20), default="XAU/USD", nullable=False)
    session_preferences = Column(
        JSONB, 
        nullable=True,
        comment="Trading session preferences: LONDON, NY, ASIA"
    )
    oanda_janitor_enabled = Column(
        Boolean, 
        default=False, 
        nullable=False,
        comment="Allow system to reconcile OANDA positions"
    )
    
    # Telegram Configuration
    telegram_bot_token = Column(
        String, 
        nullable=True,
        comment="Encrypted Telegram bot token for user's personal bot"
    )
    
    # Trading Preferences
    # supported_symbols moved to BrokerAccount
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="preferences")
    fund = relationship("Fund", foreign_keys=[default_fund_id])

    def __init__(self, **kwargs):
        """Initialize user preferences with proper defaults for JSONB fields"""
        # Set proper defaults for JSONB fields if not provided
        if 'preferred_timeframes' not in kwargs or kwargs['preferred_timeframes'] is None:
            kwargs['preferred_timeframes'] = ["4H", "1H", "15m"]
        super().__init__(**kwargs)
