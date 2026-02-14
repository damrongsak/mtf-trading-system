from sqlalchemy import Column, Integer, String, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID as Uuid
import uuid
from datetime import datetime
from app.database import Base

class OpenInterest(Base):
    __tablename__ = "open_interest"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_at = Column(DateTime, nullable=False)
    contract_symbol = Column(String(50), nullable=False)
    dte = Column(Integer, nullable=False)
    strike = Column(Numeric(18, 8), nullable=False)
    call_oi = Column(Numeric(18, 2), nullable=True)
    put_oi = Column(Numeric(18, 2), nullable=True)
    underlying_price = Column(Numeric(18, 8), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
