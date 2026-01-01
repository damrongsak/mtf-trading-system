import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.security import get_current_user
from app.models.deployment import Deployment
from app.routers.deployments import start_bot_instance, stop_bot_instance
from app.models.user_fund import User
import uuid
import httpx

@pytest.fixture
def local_mock_db():
    return MagicMock()

@pytest.fixture(autouse=True)
def override_dependency(local_mock_db):
    app.dependency_overrides[get_db] = lambda: local_mock_db
    yield
    app.dependency_overrides = {}

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = str(uuid.uuid4())
    user.username = "testuser"
    return user

@pytest.fixture
def client(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides[get_current_user] = None

from datetime import datetime, timezone
import uuid

# ...

def test_create_deployment_success(client, local_mock_db, mock_user):
    # Mock active count < 5
    local_mock_db.query.return_value.filter.return_value.count.return_value = 0
    
    def refresh_effect(obj):
        obj.id = uuid.uuid4()
        obj.started_at = datetime.now(timezone.utc)
        return None
        
    local_mock_db.refresh.side_effect = refresh_effect
    
    payload = {
        "strategy_id": str(uuid.uuid4()),
        "stock_symbol": "AAPL",
        "timeframe": "1h",
        "config_snapshot": {},
        "is_live": False
    }
    
    response = client.post("/api/v1/deployments/", json=payload)
    if response.status_code != 200:
        print(response.json())
    assert response.status_code == 200
    assert local_mock_db.add.called
    assert local_mock_db.commit.called

def test_create_deployment_limit_reached(client, local_mock_db, mock_user):
    # Mock active count >= 5
    local_mock_db.query.return_value.filter.return_value.count.return_value = 5
    
    payload = {
        "strategy_id": str(uuid.uuid4()),
        "stock_symbol": "AAPL",
        "timeframe": "1h",
        "config_snapshot": {},
        "is_live": False
    }
    
    response = client.post("/api/v1/deployments/", json=payload)
    assert response.status_code == 400
    assert "limit reached" in response.text

def test_stop_deployment_success(client, local_mock_db, mock_user):
    dep_id = str(uuid.uuid4())
    mock_dep = MagicMock(spec=Deployment)
    mock_dep.id = dep_id
    mock_dep.user_id = mock_user.id
    mock_dep.status = "ACTIVE"
    mock_dep.strategy_id = str(uuid.uuid4())
    mock_dep.stock_symbol = "AAPL"
    mock_dep.timeframe = "1h"
    mock_dep.config_snapshot = {}
    mock_dep.is_live = False
    mock_dep.started_at = datetime.utcnow()
    mock_dep.stopped_at = None
    mock_dep.last_error = None
    mock_dep.strategy = MagicMock()
    mock_dep.strategy.name = "TestStrategy"
    
    local_mock_db.query.return_value.filter.return_value.first.return_value = mock_dep
    
    response = client.post(f"/api/v1/deployments/{dep_id}/stop")
    assert response.status_code == 200
    assert mock_dep.status == "STOPPING"
    assert local_mock_db.commit.called

def test_restart_deployment_success(client, local_mock_db, mock_user):
    dep_id = str(uuid.uuid4())
    mock_dep = MagicMock(spec=Deployment)
    mock_dep.id = dep_id
    mock_dep.user_id = mock_user.id
    mock_dep.status = "STOPPED"
    mock_dep.config_snapshot = {}
    mock_dep.strategy_id = str(uuid.uuid4())
    mock_dep.stock_symbol = "AAPL"
    mock_dep.timeframe = "1h"
    mock_dep.is_live = False
    mock_dep.started_at = datetime.utcnow()
    mock_dep.stopped_at = datetime.utcnow()
    mock_dep.last_error = None
    mock_dep.strategy = MagicMock()
    mock_dep.strategy.name = "TestStrategy"
    
    local_mock_db.query.return_value.filter.return_value.first.return_value = mock_dep
    
    response = client.post(f"/api/v1/deployments/{dep_id}/restart")
    assert response.status_code == 200
    assert mock_dep.status == "STARTING"
    assert local_mock_db.commit.called

def test_restart_deployment_invalid_status(client, local_mock_db, mock_user):
    dep_id = str(uuid.uuid4())
    mock_dep = MagicMock(spec=Deployment)
    mock_dep.id = dep_id
    mock_dep.status = "ACTIVE"
    
    local_mock_db.query.return_value.filter.return_value.first.return_value = mock_dep
    
    response = client.post(f"/api/v1/deployments/{dep_id}/restart")
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_start_bot_instance_success():
    dep_id = str(uuid.uuid4())
    mock_dep = MagicMock(spec=Deployment)
    mock_dep.id = dep_id
    
    with patch("app.routers.deployments.SessionLocal") as MockSession:
        session = MockSession.return_value
        session.query.return_value.filter.return_value.first.return_value = mock_dep
        
        with patch("httpx.AsyncClient.post", return_value=MagicMock(status_code=200)) as mock_post:
            await start_bot_instance(dep_id, {})
            
            assert mock_dep.status == "ACTIVE"
            assert session.commit.called

@pytest.mark.asyncio
async def test_start_bot_instance_failure():
    dep_id = str(uuid.uuid4())
    mock_dep = MagicMock(spec=Deployment)
    mock_dep.id = dep_id
    
    with patch("app.routers.deployments.SessionLocal") as MockSession:
        session = MockSession.return_value
        session.query.return_value.filter.return_value.first.return_value = mock_dep
        
        # Helper for async http client context manager
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post.return_value = MagicMock(status_code=500, text="Error")
        
        with patch("httpx.AsyncClient", return_value=mock_client):
            await start_bot_instance(dep_id, {})
            
            assert mock_dep.status == "ERROR"
            assert session.commit.called

@pytest.mark.asyncio
async def test_stop_bot_instance_success():
    dep_id = str(uuid.uuid4())
    mock_dep = MagicMock(spec=Deployment)
    mock_dep.id = dep_id
    
    with patch("app.routers.deployments.SessionLocal") as MockSession:
        session = MockSession.return_value
        session.query.return_value.filter.return_value.first.return_value = mock_dep
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post.return_value = MagicMock(status_code=200)
        
        with patch("httpx.AsyncClient", return_value=mock_client):
            await stop_bot_instance(dep_id)
            
            assert mock_dep.status == "STOPPED"
            assert session.commit.called
