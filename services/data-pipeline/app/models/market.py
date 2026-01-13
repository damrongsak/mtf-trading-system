from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Uuid
from sqlalchemy.orm import relationship
import uuid
from app.database import Base

class MarketCategory(Base):
    __tablename__ = "market_categories"
    __table_args__ = {"extend_existing": True}

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    items = relationship("MarketSymbol", back_populates="category", cascade="all, delete-orphan")

class MarketSymbol(Base):
    __tablename__ = "market_symbols"
    __table_args__ = {"extend_existing": True}

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(Uuid(as_uuid=True), ForeignKey("market_categories.id"), nullable=False)
    data_source_id = Column(Uuid(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=True)
    
    symbol = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    category = relationship("MarketCategory", back_populates="items")
    data_source = relationship("DataSource")
