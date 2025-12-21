from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.database import Base

class MarketCategory(Base):
    __tablename__ = "market_categories"

    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False, index=True)
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    items = relationship("MarketSymbol", back_populates="category", cascade="all, delete-orphan", order_by="MarketSymbol.order_index")

class MarketSymbol(Base):
    __tablename__ = "market_symbols"

    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("market_categories.id"), nullable=False)
    symbol = Column(String, nullable=False) # e.g. "EUR_USD"
    display_name = Column(String, nullable=True) # e.g. "Euro / US Dollar"
    order_index = Column(Integer, default=0)
    
    # Ideally link to DataSource if we want specific source per symbol
    # for now, relying on StreamManager's channel convention `market_data:{symbol}`

    category = relationship("MarketCategory", back_populates="items")
