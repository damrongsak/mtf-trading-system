
from sqlalchemy import Column, String, JSON, Numeric, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base

class BrokerAccount(Base):
    __tablename__ = "broker_accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    fund_id = Column(UUID(as_uuid=True), nullable=False) # ForeignKey not enforced in execution app models usually unless imported, but field MUST exist
    
    broker_name = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    account_number = Column(String, nullable=True)
    
    credentials_encrypted = Column(JSONB, nullable=False) # Maps to jsonb in DB
    is_active = Column(Boolean, default=True)
    is_live = Column(Boolean, default=False)
    environment = Column(String, default="practice", nullable=False) # New column
    
    supported_symbols = Column(JSONB, nullable=True)
    risk_settings = Column(JSONB, nullable=True)
    
class Fund(Base):
    __tablename__ = "funds"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    strategy_type = Column(String, nullable=False) 
    max_risk_per_trade = Column(Numeric(10, 2), nullable=False)
    risk_percentage = Column(Numeric(5, 4), default=0.01) 
    asset_classes = Column(JSON, nullable=False) # execution app uses JSON for this
    default_lot_size = Column(Numeric(10, 2), nullable=False)
    max_drawdown_threshold = Column(Numeric(10, 2), nullable=True)
