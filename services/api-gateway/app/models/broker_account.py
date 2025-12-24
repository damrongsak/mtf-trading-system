from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base

class BrokerAccount(Base):
    __tablename__ = "broker_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id"), nullable=False)
    
    broker_name = Column(String(50), nullable=False) # e.g., "OANDA", "BINANCE"
    account_name = Column(String(100), nullable=False) # User-defined alias
    account_number = Column(String(100), nullable=True) # Official account ID/Number from broker
    
    credentials_encrypted = Column(String, nullable=False) # Encrypted API keys/tokens (Base64 string)
    is_active = Column(Boolean, default=True)
    is_live = Column(Boolean, default=False) # Demo vs Live
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    fund = relationship("Fund", back_populates="broker_accounts")
