import pytest
from unittest.mock import AsyncMock, patch
from app.health import verify_dependencies

@pytest.mark.asyncio
async def test_verify_dependencies_success():
    """Verify that no exception is raised when dependencies are healthy."""
    with (
        patch("app.health.redis.from_url") as mock_redis_factory,
        patch("app.health.AsyncSessionLocal") as mock_session_cls
    ):
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis_factory.return_value = mock_redis
        mock_redis.ping.return_value = True
        
        # Mock Database
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value = True
        
        # Should not raise exception
        await verify_dependencies()
        
        mock_redis.ping.assert_called_once()
        mock_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_verify_dependencies_redis_failure():
    """Verify that ConnectionError is raised when Redis fails."""
    with patch("app.health.redis.from_url") as mock_redis_factory:
        mock_redis = AsyncMock()
        mock_redis_factory.return_value = mock_redis
        mock_redis.ping.side_effect = Exception("Redis Down")
        
        with pytest.raises(ConnectionError, match="Redis unavailable"):
            await verify_dependencies()

@pytest.mark.asyncio
async def test_verify_dependencies_db_failure():
    """Verify that ConnectionError is raised when DB fails."""
    with (
        patch("app.health.redis.from_url") as mock_redis_factory,
        patch("app.health.AsyncSessionLocal") as mock_session_cls
    ):
        
        # Redis passes
        mock_redis = AsyncMock()
        mock_redis_factory.return_value = mock_redis
        
        # DB fails
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        mock_session.execute.side_effect = Exception("DB Down")
        
        with pytest.raises(ConnectionError, match="Database unavailable"):
            await verify_dependencies()