import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, UniqueConstraint, Index, Uuid
from app.database import Base

class COTRecord(Base):
    __tablename__ = "cot_records"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_date = Column(DateTime, nullable=False)
    symbol = Column(String(20), nullable=False)
    commercials_long = Column(Numeric(18, 2), nullable=False)
    commercials_short = Column(Numeric(18, 2), nullable=False)
    non_commercials_long = Column(Numeric(18, 2), nullable=False)
    non_commercials_short = Column(Numeric(18, 2), nullable=False)
    managed_money_long = Column(Numeric(18, 2), nullable=True)
    managed_money_short = Column(Numeric(18, 2), nullable=True)
    non_reportable_long = Column(Numeric(18, 2), nullable=True)
    non_reportable_short = Column(Numeric(18, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('symbol', 'report_date', name='uq_cot_records_symbol_report_date'),
        Index('ix_cot_records_report_date', 'report_date'),
        Index('ix_cot_records_symbol', 'symbol'),
    )
