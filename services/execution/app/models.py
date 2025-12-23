
from sqlalchemy import Column, String, JSON
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
