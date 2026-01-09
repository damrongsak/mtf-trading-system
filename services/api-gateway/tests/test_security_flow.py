import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.main import app
from app.database import get_db
from app.security import create_access_token
from app.models.user import User
import uuid

@pytest.fixture
def mock_db_session():
    return MagicMock()

@pytest.fixture
def override_dependency(mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    yield
    app.dependency_overrides = {}

def test_get_current_user_integration(override_dependency, mock_db_session):
    # Ensure get_current_user is NOT overridden
    app.dependency_overrides.pop("get_current_user", None)
        
    client = TestClient(app)
    
    # 1. Create a valid token
    token = create_access_token({"sub": "realuser"})
    
    # 2. Mock DB to return user
    mock_user = MagicMock(spec=User)
    mock_user.username = "realuser"
    mock_user.id = str(uuid.uuid4())
    
    # query(User).filter(...).first()
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
    
    # 3. Call a protected endpoint
    # Use /api/v1/funds/ as it requires authentication
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/funds/", headers=headers)
    
    # If authenticated, it proceeds.
    # It might return empty list or fail later if logic depends on real DB, 
    # but we just want to ensure it didn't return 401.
    assert response.status_code != 401
    
def test_get_current_user_invalid_token(override_dependency):
    app.dependency_overrides.pop("get_current_user", None)
    client = TestClient(app)
    headers = {"Authorization": "Bearer invalidtoken"}
    response = client.get("/api/v1/funds/", headers=headers)
    assert response.status_code == 401

def test_get_current_user_user_not_found(override_dependency, mock_db_session):
    app.dependency_overrides.pop("get_current_user", None)
    client = TestClient(app)
    token = create_access_token({"sub": "missinguser"})
    
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/funds/", headers=headers)
    assert response.status_code == 401
