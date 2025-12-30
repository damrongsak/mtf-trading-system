
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock, ANY
from app.main import app
from app.models.deployment import Deployment
from app.models.trade import Trade
from app.models.user_fund import User
from app.database import get_db
import uuid
from datetime import datetime

client = TestClient(app)

@pytest.fixture
def mock_db_session():
    return MagicMock()

@pytest.fixture
def override_dependency(mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    yield
    app.dependency_overrides = {}

@pytest.fixture
def mock_execution_client():
    with patch("app.routers.internal.execution_client") as mock:
        yield mock

def test_internal_signal_execution(mock_db_session, mock_execution_client, override_dependency):
    # Setup verify logic
    # We mock query(...).filter(...).first() to return the deployment
    dep_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    mock_deployment = MagicMock(spec=Deployment)
    mock_deployment.id = dep_id
    mock_deployment.user_id = user_id
    mock_deployment.status = "ACTIVE"
    mock_deployment.config_snapshot = {"broker_account_id": "acc-123"}
    
    mock_user = MagicMock(spec=User)
    mock_user.id = user_id
    
    # Mock DB Query Results
    # 1. Query Deployment
    # 2. Query User
    # 3. Query UserFund/BrokerAccount (skipped in simplified logic if snapshot has it)
    
    # We can use side_effect for db.query
    def query_side_effect(model):
        q = MagicMock()
        if model == Deployment:
            q.filter.return_value.first.return_value = mock_deployment
        elif model == User:
            q.filter.return_value.first.return_value = mock_user
        return q
    
    mock_db_session.query.side_effect = query_side_effect
    
    # Mock Execution Service Response
    mock_execution_client.place_smart_order = AsyncMock(return_value={
        "id": "ord-123",
        "instrument": "XAU_USD",
        "price": 2000.0,
        "units": 1
    })

    # Call Endpoint
    headers = {"x-internal-key": "dev-internal-key"}
    payload = {
        "deployment_id": dep_id,
        "symbol": "XAU/USD",
        "direction": "BULLISH",
        "stop_loss": 1990.0,
        "risk_usd": 50.0,
        "reason": "Test Signal"
    }
    
    response = client.post("/api/v1/internal/signals", json=payload, headers=headers)
    
    assert response.status_code == 200
    assert response.json()["id"] == "ord-123"
    
    # Verify Trade Persistence (db.add called? No, logic uses TradeService.create... which does db.add or db.commit)
    # The logic sets attributes on trade.
    # We check if db.commit() was called
    mock_db_session.commit.assert_called()

def test_deployment_pnl_aggregation(mock_db_session, override_dependency):
    # Setup Mock User
    mock_user = MagicMock(spec=User)
    mock_user.id = str(uuid.uuid4())
    
    from app.routers.deployments import get_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    # Setup Deployments
    dep1 = MagicMock(spec=Deployment)
    dep1.id = str(uuid.uuid4())
    # Model validate checks attributes, we need to ensure they exist
    dep1.user_id = mock_user.id
    dep1.stock_symbol = "AAPL"
    dep1.status = "ACTIVE"
    dep1.config_snapshot = {}
    dep1.started_at = datetime.utcnow()
    dep1.stopped_at = None
    dep1.last_error = None
    dep1.last_signal_at = None
    
    dep2 = MagicMock(spec=Deployment)
    dep2.id = str(uuid.uuid4())
    dep2.user_id = mock_user.id
    dep2.stock_symbol = "GOOG"
    dep2.status = "ACTIVE"
    dep2.config_snapshot = {}
    dep2.started_at = datetime.utcnow()
    
    # DB Queries Sequence:
    # 1. Query Deployments -> list
    # 2. Query PnL for Dep1 -> 80.0
    # 3. Query PnL for Dep2 -> 50.0
    
    # We need to structure the mock carefully.
    # The router calls:
    # deployments = db.query(Deployment).filter(...).offset(...).limit(...).all()
    # Then loop:
    # total_pnl = db.query(func.sum(Trade.pnl_usd)).filter(...).scalar()
    
    mock_query_deps = MagicMock()
    mock_query_deps.filter.return_value.offset.return_value.limit.return_value.all.return_value = [dep1, dep2]
    
    mock_query_pnl = MagicMock()
    # scalar() side effect for sequential calls
    mock_query_pnl.filter.return_value.scalar.side_effect = [80.0, 50.0]
    
    def query_side_effect(*args):
        if args and args[0] is Deployment:
            return mock_query_deps
        # args[0] might be func.sum(...)
        return mock_query_pnl

    mock_db_session.query.side_effect = query_side_effect
    
    # Call Endpoint
    response = client.get("/api/v1/deployments/")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 2
    assert data[0]["id"] == str(dep1.id)
    assert data[0]["total_pnl_usd"] == 80.0
    assert data[1]["id"] == str(dep2.id)
    assert data[1]["total_pnl_usd"] == 50.0
