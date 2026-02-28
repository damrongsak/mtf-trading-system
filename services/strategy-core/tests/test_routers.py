
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from app.main import app
from app.database import get_db

client = TestClient(app)

# Signal ID for reuse
import uuid
TEST_SIG_ID = str(uuid.uuid4())

@pytest.fixture
def mock_db_session():
    mock_db = MagicMock()
    # Mocking SignalLog query
    from app.models.signal_log import SignalLog
    mock_signal = SignalLog(
        id=uuid.UUID(TEST_SIG_ID), 
        status="PENDING_APPROVAL", 
        strategy_name="Strategy-1", 
        symbol="XAU_USD", 
        direction="LONG"
    )
    mock_db.query.return_value.filter.return_value.first.return_value = mock_signal
    yield mock_db

@pytest.fixture(autouse=True)
def override_db(mock_db_session):
    def _get_db_override():
        yield mock_db_session
    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def mock_workers():
    from app.database import engine, Base
    if engine:
        Base.metadata.create_all(engine)
    with patch("app.main.strategy_engine.start", new_callable=AsyncMock), \
         patch("app.main.live_runner.start", new_callable=AsyncMock), \
         patch("app.fleet.FleetManager.load_fleet", new_callable=AsyncMock), \
         patch("app.main.reconciliation_worker.start", new_callable=AsyncMock), \
         patch("app.main.reconciliation_worker.stop", new_callable=AsyncMock):
        yield

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_execution_flow_router_manual(mock_workers, mock_db_session):
    with patch("app.routers.execution_flow.execution_client") as mock_client, \
         patch("app.routers.execution_flow.config_cache") as mock_cache:
         
         mock_client.place_order = AsyncMock(return_value={"id": "exec_1"})
         mock_cache.get_config.return_value = {"broker_account_id": "test_acc"}
         
         response = client.post(f"/api/v1/signals/{TEST_SIG_ID}/approve")
         assert response.status_code == 200
         assert response.json()["status"] == "executed"

def test_market_router_regime(mock_workers):
    with patch("app.routers.market.fetch_candles_logic") as mock_fetch:
         import pandas as pd
         df = pd.DataFrame({
             "close": [100, 101, 102, 103, 104],
             "high": [101, 102, 103, 104, 105],
             "low": [99, 100, 101, 102, 103],
             "open": [100, 101, 102, 103, 104]
         })
         df.index = pd.date_range("2024-01-01", periods=5, freq="H")
         mock_fetch.return_value = df
         
         payload = {"symbol": "XAUUSD", "timeframe": "H1", "bias": "BULLISH"}
         response = client.post("/api/v1/market/regime", json=payload)
         assert response.status_code == 200

def test_quant_router_analyze(mock_workers):
    payload = {"symbol": "XAU_USD", "timeframe": "H1"}
    with patch("app.market_data.market_data_manager.get_candles") as mock_get:
         import pandas as pd
         df = pd.DataFrame({"close": [100]*200, "high": [101]*200, "low": [99]*200, "open": [100]*200})
         df.index = pd.date_range("2024-01-01", periods=200, freq="H")
         mock_get.return_value = df
         response = client.post("/api/v1/quant/analyze", json=payload)
         assert response.status_code == 200

def test_risk_router_check(mock_workers):
    payload = {
        "symbol": "XAU_USD",
        "entry_price": 2000.0,
        "stop_loss": 1990.0,
        "take_profit": 2020.0,
        "account_balance": 10000.0
    }
    response = client.post("/api/v1/risk/check", json=payload)
    assert response.status_code == 200
