
from sqlalchemy import Column, String, JSON, Numeric
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class BrokerAccount(Base):
    __tablename__ = "broker_accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    broker_name = Column(String, nullable=False)
    # Storing credentials securely? For MVP it's in DB. 
    # In production use Vault.
    credentials = Column(JSON, nullable=False)
    account_id = Column(String, nullable=False)
    fund_id = Column(UUID(as_uuid=True), nullable=True) # Check schema, strictly nullable=False?
    supported_symbols = Column(JSON, nullable=True)
    risk_settings = Column(JSON, nullable=True)
    
class Fund(Base):
    __tablename__ = "funds"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    strategy_type = Column(String, nullable=False) # Enum as string
    max_risk_per_trade = Column(Numeric(10, 2), nullable=False)
    asset_classes = Column(JSON, nullable=False)
    # Add other risk params as needed, or just mapped broadly
    default_lot_size = Column(Numeric(10, 2), nullable=False)
    max_drawdown_threshold = Column(Numeric(10, 2), nullable=True)
