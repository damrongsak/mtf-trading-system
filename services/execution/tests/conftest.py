import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import app
from app.database import get_db

@pytest.fixture(autouse=True)
def clean_overrides():
    """Clear FastAPI dependency overrides after each test."""
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture(autouse=True)
def global_cache_mock():
    """Globally mock execution_cache to prevent state leaking and await errors."""
    with patch("app.services.order_service.execution_cache") as mock_cache, \
         patch("app.services.cache_service.execution_cache", mock_cache):
        
        mock_cache.get_account = AsyncMock(return_value=None)
        mock_cache.get_fund = AsyncMock(return_value=None)
        mock_cache.get_risk_filters = AsyncMock(return_value=None)
        mock_cache.get_credentials = AsyncMock(return_value=None)
        mock_cache.set_account = AsyncMock()
        mock_cache.set_fund = AsyncMock()
        mock_cache.set_risk_filters = AsyncMock()
        mock_cache.set_credentials = MagicMock()
        
        yield mock_cache

@pytest.fixture
def test_client(mock_db):
    """Provides a TestClient with auth and DB already overridden."""
    from app.main import verify_internal_api_key
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[verify_internal_api_key] = lambda: "test-auth"
    
    # We yield the client. Settings patch is handled per test if needed, 
    # but verify_internal_api_key is already overridden.
    yield TestClient(app)
