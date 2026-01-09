
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.streaming.subscriber import RedisSubscriber
import json

@pytest.fixture
def mock_redis():
    with patch("app.streaming.subscriber.redis.from_url") as mock:
        # redis.from_url(url) -> client object (not awaitable usually, but in async redis it returns a client)
        # client.pubsub() -> pubsub object (not awaitable)
        mock_client = MagicMock() 
        mock.return_value = mock_client
        
        mock_pubsub = AsyncMock()
        # Ensure listen is a MagicMock (sync call returning iterator), NOT AsyncMock
        # because _listen() does `async for msg in pubsub.listen()`
        # If listen is AsyncMock, it returns a coroutine, which async for cannot iterate.
        # The fixture provides a default, but tests calling _listen directly should override this
        # with a specific async iterator for their test case.
        mock_pubsub.listen = MagicMock(return_value=ExampleAsyncIterable())
        
        mock_client.pubsub.return_value = mock_pubsub
        
        yield mock_client

class ExampleAsyncIterable:
    def __aiter__(self):
        return self
    async def __anext__(self):
        # Stop immediately by default
        raise StopAsyncIteration

@pytest.mark.asyncio
async def test_subscriber_connect(mock_redis):
    callback = AsyncMock()
    subscriber = RedisSubscriber(callback)
    await subscriber.connect()
    assert subscriber.is_running
    mock_redis.pubsub.assert_called_once()

@pytest.mark.asyncio
async def test_subscriber_psubscribe(mock_redis):
    callback = AsyncMock()
    subscriber = RedisSubscriber(callback)
    await subscriber.psubscribe(["pattern1", "pattern2"])
    
    # Check if connect was auto-called
    assert subscriber.is_running
    subscriber.pubsub.psubscribe.assert_awaited_with("pattern1", "pattern2")

@pytest.mark.asyncio
async def test_subscriber_message_handling(mock_redis):
    callback = AsyncMock()
    subscriber = RedisSubscriber(callback)
    await subscriber.connect()
    
    # Mock pubsub.listen to return a list of messages
    # Note: async generator mocking in Python < 3.8/with simple mocks can be tricky.
    # We simulate the iterator
    
    mock_msg = {
        'type': 'pmessage',
        'channel': 'test_channel',
        'data': json.dumps({'price': 100})
    }
    
    # Setup mock iterator for listen
    async def mock_listen_gen():
        yield mock_msg
    
    # IMPORTANT: listen() is awaited? No, listen() returns a generator.
    # In redis-py async: async for msg in pubsub.listen(): ...
    # So pubsub.listen() is a method that returns an AsyncIterator.
    # If pubsub is AsyncMock, pubsub.listen() returns a Coroutine -> AsyncIterator? 
    # No, AsyncMock.listen() returns a Coroutine.
    # We need pubsub.listen to be a method that returns the generator directly (or a coroutine that returns it? No, async for doesn't await the iterable expression if it's a function call... wait, it does `iter = (await expr).__aiter__()` if expr is awaitable?)
    # Python `async for x in func()`: 
    # If func is async def, it returns a coroutine. You can't `async for` a coroutine unless that coroutine returns an async iterable. 
    # redis-py `listen()` is NOT async def?
    # Actually `pubsub.listen()` in redis-py is a sync method returning a generator in sync mode.
    # In async mode? `async for message in pubsub.listen():`
    # Let's assume it returns an async generator.
    
    # To mock this correctly with AsyncMock involved:
    # subscriber.pubsub is AsyncMock. subscriber.pubsub.listen is AsyncMock.
    # Calling it returns a Coroutine.
    # We want it to be an AsyncIterator.
    
    # Override listen to be a MagicMock that returns the async generator
    subscriber.pubsub.listen = MagicMock(return_value=mock_listen_gen())
    
    # Run the listener (it runs in background task in connect, but we can call _listen directly for test)
    # We use a timeout or separate task to avoid infinite loop if _listen loops forever
    # But _listen loops on self.pubsub.listen(), which yields once here.
    
    await subscriber._listen()
    
    callback.assert_awaited_with('test_channel', {'price': 100})

@pytest.mark.asyncio
async def test_subscriber_unsubscribe(mock_redis):
    callback = AsyncMock()
    subscriber = RedisSubscriber(callback)
    await subscriber.connect() # sets self.pubsub
    
    # Unsubscribe
    await subscriber.unsubscribe(["channel1"])
    subscriber.pubsub.unsubscribe.assert_awaited_with("channel1")
    
    # PUnsubscribe
    await subscriber.punsubscribe(["pattern1"])
    subscriber.pubsub.punsubscribe.assert_awaited_with("pattern1")

@pytest.mark.asyncio
async def test_subscriber_error_handling(mock_redis):
    callback = AsyncMock()
    subscriber = RedisSubscriber(callback)
    await subscriber.connect()
    
    # 1. Invalid JSON
    mock_bad_msg = {'type': 'message', 'channel': 'ch1', 'data': 'invalid_json'}
    
    # 2. JSON Array/String that is valid JSON but maybe engine expects dict? 
    # The code just loads it. If loading fails -> error.
    
    async def mock_listen_gen():
        yield mock_bad_msg
        
    subscriber.pubsub.listen = MagicMock(return_value=mock_listen_gen())
    
    # Should log error but not crash
    await subscriber._listen()
    
    # Callback NOT called
    callback.assert_not_called()


