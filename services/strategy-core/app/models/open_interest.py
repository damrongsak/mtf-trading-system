import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, DateTime, UniqueConstraint, Index, Uuid
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
    underlying_contract_symbol = Column(String(50), nullable=True)
    implied_volatility = Column(Numeric(18, 8), nullable=True, comment="Synthetic or derived Implied Volatility (GVZ baseline + Skew)")
    delta = Column(Numeric(18, 8), nullable=True)
    gamma = Column(Numeric(18, 8), nullable=True)
    vega = Column(Numeric(18, 8), nullable=True)
    theta = Column(Numeric(18, 8), nullable=True)
    vanna = Column(Numeric(18, 8), nullable=True, comment="Sensitivity of Option Delta to changes in IV (dDelta/dVol)")
    charm = Column(Numeric(18, 8), nullable=True, comment="Rate of Change of Option Delta over time (Delta Decay)")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('contract_symbol', 'strike', 'snapshot_at', name='uq_open_interest_contract_strike_snapshot'),
        Index('ix_open_interest_snapshot_at_symbol', 'snapshot_at', 'contract_symbol'),
        Index('ix_open_interest_dte', 'dte'),
        Index('ix_open_interest_snapshot_at', 'snapshot_at'),
        Index('ix_open_interest_contract_symbol', 'contract_symbol'),
    )
