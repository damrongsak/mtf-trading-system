import pytest
import redis.asyncio as redis

def test_redis_import():
    """Verify that redis can be imported."""
    assert redis is not None

@pytest.mark.asyncio
async def test_redis_connection_mock():
    """Verify we can instantiate a redis client (even if not connecting)."""
    # Just checking instantiation doesn't fail
    r = redis.Redis.from_url("redis://localhost")
    assert r is not None
    await r.close()
