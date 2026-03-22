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
    """BRUTE FORCE mock for execution_cache to ensure all references are patched."""
    from app.services.cache_service import execution_cache as global_cache
    from app.services.order_service import execution_cache as order_cache
    
    mock_get_account = AsyncMock(return_value=None)
    mock_get_fund = AsyncMock(return_value=None)
    mock_get_filters = AsyncMock(return_value=[])
    mock_get_creds = AsyncMock(return_value=None)
    
    # Override methods on both references
    for cache in [global_cache, order_cache]:
        cache.get_account = mock_get_account
        cache.get_fund = mock_get_fund
        cache.get_risk_filters = mock_get_filters
        cache.get_credentials = mock_get_creds
        cache.set_account = AsyncMock()
        cache.set_fund = AsyncMock()
        cache.set_credentials = AsyncMock()

    mock_aggregator = MagicMock()
    mock_aggregator.get_account = mock_get_account
    mock_aggregator.get_fund = mock_get_fund
    mock_aggregator.get_risk_filters = mock_get_filters
    mock_aggregator.get_credentials = mock_get_creds
    
    yield mock_aggregator

@pytest.fixture
def test_client(mock_db):
    """Provides a TestClient with auth and DB already overridden."""
    from app.main import verify_internal_api_key
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[verify_internal_api_key] = lambda: "test-auth"
    yield TestClient(app)
