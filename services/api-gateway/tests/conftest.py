import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import sys
import os

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.main import app
from app.database import get_db
from app.models.user import User

import uuid
from datetime import datetime, timezone

@pytest.fixture
def mock_db_session():
    """Returns a mock SQLAlchemy session"""
    session = MagicMock(spec=Session)
    
    def simulate_refresh(instance, attribute_names=None, with_for_update=None):
        if not hasattr(instance, 'id') or instance.id is None:
            instance.id = uuid.uuid4()
        if not hasattr(instance, 'is_active') or instance.is_active is None:
            instance.is_active = True
        if not hasattr(instance, 'created_at') or instance.created_at is None:
            instance.created_at = datetime.now(timezone.utc)
        if not hasattr(instance, 'updated_at') or instance.updated_at is None:
            instance.updated_at = datetime.now(timezone.utc)

    session.refresh.side_effect = simulate_refresh
    return session

@pytest.fixture
def client(mock_db_session):
    """Returns a TestClient with overridden get_db dependency"""
    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def mock_current_user():
    """Returns a mock user object"""
    user = MagicMock(spec=User)
    user.id = "123e4567-e89b-12d3-a456-426614174000"
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_active = True
    user.avatar_url = None
    return user
@pytest.fixture(autouse=True)
def mock_redis():
    """Mocks redis_client to avoid connection issues in tests"""
    with patch("app.utils.cache.redis_client", new_callable=AsyncMock) as mock:
        mock.get_client.return_value = AsyncMock()
        mock.get_client.return_value.get.return_value = None
        mock.get_client.return_value.setex.return_value = True
        yield mock
