from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.database import Base

class TransactionType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id"), nullable=False)
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Numeric(18, 8), nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    status = Column(String(50), default="COMPLETED")
    reference = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    payment_method = Column(String(50), nullable=True)
    trading_account = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    fund = relationship("Fund", back_populates="transactions")
