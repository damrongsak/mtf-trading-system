from sqlalchemy import Column, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base

class PortfolioAllocation(Base):
    __tablename__ = "portfolio_allocations"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id"), nullable=False)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=False)
    
    weight = Column(Numeric(5, 4), nullable=False) # 0.0000 to 1.0000
    volatility_target = Column(Numeric(5, 2), nullable=True)
    last_rebalance = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    fund = relationship("Fund", back_populates="allocations")
    strategy = relationship("Strategy", back_populates="allocations")
