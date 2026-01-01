import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.utils.redis_subscriber import RedisSubscriber

@pytest.fixture
def subscriber():
    return RedisSubscriber()

@pytest.mark.asyncio
async def test_connect(subscriber):
    with patch("app.utils.redis_subscriber.redis.from_url") as mock_from_url:
        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_from_url.return_value = mock_redis
        
        await subscriber.connect()
        
        mock_from_url.assert_called_once()
        assert subscriber.redis is mock_redis
        assert subscriber.pubsub is mock_pubsub

@pytest.mark.asyncio
async def test_subscribe(subscriber):
    with patch("app.utils.redis_subscriber.redis.from_url"):
        # subscriber needs connect
        subscriber.pubsub = AsyncMock() # subscribe is async
        
        await subscriber.subscribe(["ch1", "ch2"])
        
        subscriber.pubsub.subscribe.assert_awaited_with("ch1", "ch2")

@pytest.mark.asyncio
async def test_listen(subscriber):
    with patch("app.utils.redis_subscriber.redis.from_url"):
        # Mock pubsub.listen returning async generator
        async def async_gen():
            yield "msg1"
            yield "msg2"
            
        subscriber.pubsub = MagicMock()
        subscriber.pubsub.listen.return_value = async_gen()
        
        messages = []
        async for msg in subscriber.listen():
            messages.append(msg)
            
        assert messages == ["msg1", "msg2"]

@pytest.mark.asyncio
async def test_close(subscriber):
    mock_redis = AsyncMock()
    mock_pubsub = AsyncMock()
    
    subscriber.redis = mock_redis
    subscriber.pubsub = mock_pubsub
    
    await subscriber.close()
    
    mock_pubsub.aclose.assert_awaited()
    mock_redis.aclose.assert_awaited()
    assert subscriber.redis is None

@pytest.mark.asyncio
async def test_unsubscribe(subscriber):
    subscriber.pubsub = AsyncMock()
    await subscriber.unsubscribe()
    subscriber.pubsub.unsubscribe.assert_awaited()

@pytest.mark.asyncio
async def test_subscribe_auto_connect(subscriber):
    with patch("app.utils.redis_subscriber.redis.from_url") as mock_from_url:
        mock_redis = MagicMock()
        mock_pubsub = AsyncMock() # Fix: must be awaitable
        mock_redis.pubsub.return_value = mock_pubsub
        mock_from_url.return_value = mock_redis
        
        subscriber.pubsub = None # Force connect logic
        
        await subscriber.subscribe(["ch"])
        
        mock_from_url.assert_called() # Connect called
        mock_pubsub.subscribe.assert_awaited_with("ch")

@pytest.mark.asyncio
async def test_get_message(subscriber):
    subscriber.pubsub = AsyncMock()
    subscriber.pubsub.get_message.return_value = "hello"
    
    res = await subscriber.get_message()
    assert res == "hello"
    subscriber.pubsub.get_message.assert_awaited_with(ignore_subscribe_messages=True)

@pytest.mark.asyncio
async def test_get_message_no_pubsub(subscriber):
    subscriber.pubsub = None
    res = await subscriber.get_message()
    assert res is None
