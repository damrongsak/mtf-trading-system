import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models.user_fund import User
import uuid
from datetime import datetime, timedelta, timezone

@pytest.fixture
def local_mock_db():
    return MagicMock()

from app.routers.auth import oauth2_scheme

from app.routers.dashboard import get_current_user

# Global mock user
mock_user_instance = MagicMock(spec=User)
mock_user_instance.id = uuid.uuid4()

@pytest.fixture(autouse=True)
def override_dependency(local_mock_db):
    app.dependency_overrides[get_db] = lambda: local_mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user_instance
    yield
    app.dependency_overrides = {}

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_get_stats_empty(client, local_mock_db):
    # Setup mock user
    mock_user_instance.id = uuid.uuid4()
    
    # count() = 0
    local_mock_db.query.return_value.filter.return_value.count.return_value = 0
    response = client.get("/api/v1/dashboard/stats")
    assert response.status_code == 200
    assert response.json()["total_trades"] == 0

def test_get_stats_data(client, local_mock_db):
    mock_user_instance.id = uuid.uuid4()
    
    q = local_mock_db.query.return_value.filter.return_value
    # Enable chaining so that filter() returns the same mock
    q.filter.return_value = q
    
    # Now all count() calls go to q.count
    # total_trades = 10, winning = 6, losing = 4, open = 3
    q.count.side_effect = [10, 6, 4, 3] 
    
    # with_entities returns aggregation mock, we need to handle that too
    # query.with_entities(...) -> returns new mock usually
    # total_pnl, avg_win, avg_loss
    q.with_entities.return_value.scalar.side_effect = [100.0, 20.0, -10.0] 
    
    # BUT wait, the code is: base_query.filter(Trade.pnl_usd > 0).with_entities(...)
    # If base_query.filter returns q, then q.with_entities returns q.with_entities.return_value
    # BUT base_query.with_entities (for total_pnl) is also called on q.
    # So q.with_entities returns the SAME mock for all calls?
    # Yes, so side_effect on scalar() should work.
    
    response = client.get("/api/v1/dashboard/stats")
    
    if response.status_code != 200:
        print(f"DEBUG: {response.json()}")
        
    assert response.status_code == 200
    assert response.json()["total_trades"] == 10
    assert response.json()["winning_trades"] == 6

def test_get_equity_curve(client, local_mock_db):
    mock_user_instance.id = uuid.uuid4()
    
    trade = MagicMock()
    trade.exit_timestamp = datetime.now(timezone.utc)
    trade.pnl_usd = 50.0
    
    local_mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [trade]
    
    response = client.get("/api/v1/dashboard/equity-curve")
    assert response.status_code == 200
    assert len(response.json()) > 0
    assert response.json()[-1]["daily_pnl"] == 50.0

def test_get_performance(client, local_mock_db):
    mock_user_instance.id = uuid.uuid4()
    
    res = MagicMock()
    res.strategy_name = "Strat1"
    res.total_trades = 5
    res.total_pnl = 100.0
    res.wins = 3
    
    local_mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [res]
    
    response = client.get("/api/v1/dashboard/performance")
    assert response.status_code == 200
    assert response.json()[0]["strategy_name"] == "Strat1"
