import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.trade import Trade, TradeStatus, TradeDirection
from app.database import Base
import uuid
import os
from datetime import datetime, timezone

# Connect to DB (assuming localhost for running outside docker or service name inside)
# If running via docker compose exec api-gateway, localhost is the container itself, but db is at 'host.docker.internal' or 'postgresql'
# Wait, inside api-gateway container, DB is at 'host.docker.internal' (based on docker-compose).
# So:
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trader:trader@host.docker.internal:5432/mtf_db")

@pytest.fixture
def db_session():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_create_micro_lot_trade(db_session):
    """
    Verify that a trade with lot_size 0.0001 can be inserted.
    """
    trade = Trade(
        trade_id=uuid.uuid4(),
        symbol="AUD/USD",
        strategy_name="Test Micro Lot",
        signal_timestamp=datetime.now(timezone.utc),
        status=TradeStatus.OPEN,
        direction=TradeDirection.SHORT,
        entry_price=0.6500,
        sl_price=0.6550,
        tp_price=0.6400,
        lot_size=0.0001,  # The critical value
        risk_usd=1.0,
        rr_ratio=2.0
    )
    
    db_session.add(trade)
    db_session.commit()
    db_session.refresh(trade)
    
    from decimal import Decimal
    assert trade.lot_size == Decimal('0.0001')
    assert trade.status == TradeStatus.OPEN
    
    # Clean up
    db_session.delete(trade)
    db_session.commit()
