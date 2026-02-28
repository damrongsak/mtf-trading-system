
import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app, startup_event, shutdown_event
from app.workers.reconciliation import ReconciliationWorker
from app.workers.indicator_worker import IndicatorWorker
from app.database import Base, engine, SessionLocal, get_db
from app.models.open_interest import OpenInterest

@pytest.mark.asyncio
async def test_reconciliation_worker_one_loop():
    worker = ReconciliationWorker()
    worker.subscriber = MagicMock()
    worker.subscriber.connect = AsyncMock()
    
    with patch("app.workers.reconciliation.asyncio.sleep", side_effect=[None, Exception("Stop loop")]):
         try:
            await worker.start()
         except Exception:
             pass

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    import uuid
    # Add mock data
    now = datetime.utcnow()
    oi = OpenInterest(
        id=str(uuid.uuid4()), # Explicitly string for SQLite
        strike=2000.0,
        call_oi=1000.0,
        put_oi=500.0,
        underlying_price=2000.0,
        snapshot_at=now,
        dte=10,
        contract_symbol="XAUUSD"
    )
    db.add(oi)
    db.commit()
    db.refresh(oi)
    
    def _get_db_override():
        yield db
            
    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.clear()
    db.close()

@pytest.mark.asyncio
async def test_indicator_worker_one_loop():
    worker = IndicatorWorker()
    worker.db = MagicMock()
    
    with patch("app.workers.indicator_worker.asyncio.sleep", side_effect=[None, Exception("Stop loop")]):
         try:
            await worker.run()
         except Exception:
             pass

@pytest.mark.asyncio
async def test_app_lifespan_events():
    # Trigger startup/shutdown to cover main.py setup logic
    with patch("app.main.strategy_engine", AsyncMock()), \
         patch("app.main.live_runner", AsyncMock()), \
         patch("app.main.reconciliation_worker", AsyncMock()):
         
         await startup_event()
         await shutdown_event()

def test_main_indicators_endpoints():
    client = TestClient(app)
    
    # Test EMA
    response = client.post("/api/v1/calculate/ema", json={"data": [10.0, 11.0, 12.0], "params": {"span": 2}})
    assert response.status_code == 200
    
    # Test ATR
    response = client.post("/api/v1/calculate/atr", json={"high": [12.0, 13.0], "low": [10.0, 11.0], "close": [11.0, 12.0], "window": 1})
    assert response.status_code == 200
