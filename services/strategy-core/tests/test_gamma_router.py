
import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, SessionLocal, Base, engine
from app.models.open_interest import OpenInterest
from app.routers.gamma import get_fetch_candles

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    import uuid
    # Add mock data
    now = datetime.utcnow()
    oi1 = OpenInterest(
        id=str(uuid.uuid4()), # Explicitly string for SQLite
        strike=2000.0,
        call_oi=1000.0,
        put_oi=500.0,
        underlying_price=2000.0,
        snapshot_at=now,
        dte=10,
        contract_symbol="XAUUSD"
    )
    oi2 = OpenInterest(
        id=str(uuid.uuid4()),
        strike=2050.0,
        call_oi=5000.0,
        put_oi=100.0,
        underlying_price=2000.0,
        snapshot_at=now,
        dte=90,
        contract_symbol="XAUUSD"
    )
    db.add(oi1)
    db.add(oi2)
    db.commit()
    db.refresh(oi1)
    db.refresh(oi2)
    
    def _get_db_override():
        yield db
            
    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.clear()
    db.close()

def test_get_gamma_levels_success():
    df = pd.DataFrame({"close": [2000.0]*10, "high": [2001.0]*10, "low": [1999.0]*10, "open": [2000.0]*10, "volume": [100.0]*10})
    df.index = pd.date_range("2024-01-01", periods=10, freq="H")
    
    # Use a real async function to avoid AsyncMock issues
    async def mock_fetch(*args, **kwargs):
        return df

    app.dependency_overrides[get_fetch_candles] = lambda: mock_fetch
    
    try:
        response = client.get("/api/v1/analysis/gamma/levels?symbol=XAUUSD")
        assert response.status_code == 200
        data = response.json()
        assert "levels" in data
        assert "regime" in data
        assert data["snapshot_at"] is not None
        
        # Test DTE filtering
        response_filtered = client.get("/api/v1/analysis/gamma/levels?symbol=XAUUSD&max_dte=30")
        assert response_filtered.status_code == 200
        data_filtered = response_filtered.json()
        
        # Verify call wall is different when filtering out the 90-DTE 5000 Call OI
        heat_filtered = data_filtered.get("heatmap", [])
        assert len(heat_filtered) > 0
        strikes = [h["strike"] for h in heat_filtered]
        assert 2000.0 in strikes
        assert 2050.0 not in strikes
    finally:
        if get_fetch_candles in app.dependency_overrides:
            del app.dependency_overrides[get_fetch_candles]

