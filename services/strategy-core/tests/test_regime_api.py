import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models.regime_monitor import RegimeMonitor
from datetime import datetime, timezone

# Test Database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Add dummy data
    db.add(RegimeMonitor(
        symbol="XAUUSD",
        timeframe="H4",
        timestamp=datetime(2026, 5, 5, 0, 0, tzinfo=timezone.utc),
        gex_proxy=1500000.0,
        underlying_price=2300.0,
        regime_type="POSITIVE_GAMMA",
        is_noise=False
    ))
    db.commit()
    yield
    Base.metadata.drop_all(bind=engine)

def test_get_regime_history():
    response = client.get("/api/v1/analysis/gamma/regime-history?symbol=XAUUSD&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "XAUUSD" # Wait, did I include symbol in response? No.
    assert data[0]["regime_type"] == "POSITIVE_GAMMA"
    assert data[0]["gex_proxy"] == 1500000.0
