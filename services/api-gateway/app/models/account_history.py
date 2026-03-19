from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.database import Base

class AccountHistory(Base):
    __tablename__ = "account_history"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    broker_account_id = Column(UUID(as_uuid=True), ForeignKey("broker_accounts.id"), nullable=False, index=True)
    
    balance = Column(Numeric(18, 2), nullable=False)
    equity = Column(Numeric(18, 2), nullable=False)
    used_margin = Column(Numeric(18, 2), nullable=False)
    free_margin = Column(Numeric(18, 2), nullable=False)
    margin_level = Column(Numeric(10, 2), nullable=True)
    unrealized_gross = Column(Numeric(18, 2), nullable=True)
    unrealized_net = Column(Numeric(18, 2), nullable=True)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
