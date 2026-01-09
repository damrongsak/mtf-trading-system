import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models.user import User
import uuid
from datetime import datetime, timedelta, timezone

@pytest.fixture
def local_mock_db():
    return MagicMock()

from app.routers.auth import oauth2_scheme

from app.routers.auth import oauth2_scheme, get_current_user

# Global mock user to control from tests
mock_user_instance = MagicMock(spec=User)
mock_user_instance.id = uuid.uuid4()
mock_user_instance.username = "mockuser"
mock_user_instance.email = "mock@example.com"
mock_user_instance.is_active = True

@pytest.fixture(autouse=True)
def override_dependency(local_mock_db):
    app.dependency_overrides[get_db] = lambda: local_mock_db
    # Override get_current_user directly to avoid token decoding
    app.dependency_overrides[get_current_user] = lambda: mock_user_instance
    yield
    app.dependency_overrides = {}

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_login_success(client, local_mock_db):
    user = MagicMock(spec=User)
    user.username = "test"
    user.id = uuid.uuid4()
    user.password_hash = "hashed"
    user.email = "test@example.com"
    user.is_active = True
    user.avatar_url = None # Fix Pydantic
    
    local_mock_db.query.return_value.filter.return_value.first.return_value = user
    
    with patch("app.routers.auth.verify_password", return_value=True):
        with patch("app.routers.auth.create_access_token", return_value="token"):
             response = client.post("/api/v1/auth/token", data={"username": "test", "password": "pw"})
             assert response.status_code == 200
             assert response.json()["auth"]["access_token"] == "token"

def test_login_fail(client, local_mock_db):
    local_mock_db.query.return_value.filter.return_value.first.return_value = None
    response = client.post("/api/v1/auth/token", data={"username": "test", "password": "pw"})
    assert response.status_code == 401

def test_register_success(client, local_mock_db):
    local_mock_db.query.return_value.filter.return_value.first.return_value = None # No existing user
    
    with patch("app.routers.auth.get_password_hash", return_value="hashed"):
        with patch("app.routers.auth.create_access_token", return_value="token"):
            def add_effect(u):
                u.id = uuid.uuid4()
                u.is_active = True # Fix Pydantic
                u.avatar_url = None
                
            local_mock_db.refresh.side_effect = add_effect
            
            payload = {"username": "new", "email": "new@example.com", "password": "pw"}
            response = client.post("/api/v1/auth/register", json=payload)
            if response.status_code != 200:
                print(f"DEBUG REGISTER: {response.json()}")
            assert response.status_code == 200
            local_mock_db.add.assert_called_once()
            
def test_get_profile(client, local_mock_db):
    mock_user_instance.id = uuid.uuid4()
    mock_user_instance.username = "u"
    mock_user_instance.email = "e"
    mock_user_instance.is_active = True
    mock_user_instance.avatar_url = None # Fix Pydantic
    
    response = client.get("/api/v1/auth/profile")
    assert response.status_code == 200
    assert response.json()["data"]["username"] == "u"

def test_update_profile(client, local_mock_db):
    mock_user_instance.id = uuid.uuid4()
    mock_user_instance.username = "old"
    mock_user_instance.email = "old@example.com"
    mock_user_instance.is_active = True # Ensure active
    mock_user_instance.avatar_url = None
    
    local_mock_db.query.return_value.filter.return_value.first.return_value = None # Unique check passes
    
    payload = {"username": "new"}
    response = client.put("/api/v1/auth/profile", json=payload)
    
    assert response.status_code == 200
    assert mock_user_instance.username == "new"

def test_change_password(client, local_mock_db):
    mock_user_instance.password_hash = "old_hash"
    
    with patch("app.routers.auth.verify_password", return_value=True):
        with patch("app.routers.auth.get_password_hash", return_value="new_hash"):
            payload = {"old_password": "p", "new_password": "new"}
            response = client.put("/api/v1/auth/password", json=payload)
            assert response.status_code == 200
            assert mock_user_instance.password_hash == "new_hash"
