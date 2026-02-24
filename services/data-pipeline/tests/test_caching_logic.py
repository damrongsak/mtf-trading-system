import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.streaming.manager import StreamManager
from app.streaming.publisher import RedisPublisher
import time

@pytest.mark.asyncio
async def test_redis_publisher_publish_with_cache():
    publisher = RedisPublisher()
    publisher.redis = MagicMock()
    mock_pipeline = MagicMock()
    publisher.redis.pipeline.return_value = mock_pipeline
    mock_pipeline.execute = AsyncMock()

    channel = "test_channel"
    cache_key = "test_cache"
    message = {"data": "test"}
    cache_mapping = {"bid": 1.0, "ask": 1.1}

    await publisher.publish_with_cache(channel, cache_key, message, cache_mapping)

    publisher.redis.pipeline.assert_called_once()
    mock_pipeline.publish.assert_called_once()
    mock_pipeline.hset.assert_called_once_with(cache_key, mapping=cache_mapping)
    mock_pipeline.execute.assert_called_once()

@pytest.mark.asyncio
async def test_stream_manager_publish_callback_price_event():
    with patch("app.streaming.manager.RedisPublisher") as MockPublisher, \
         patch("app.streaming.manager.time.time", return_value=123456789.0):
        
        publisher_instance = MockPublisher.return_value
        publisher_instance.publish_with_cache = AsyncMock()
        publisher_instance.connect = AsyncMock()
        
        manager = StreamManager()
        manager.publisher = publisher_instance
        
        # Test PRICE event from cTrader
        price_data = {
            "type": "price",
            "source": "ctrader",
            "instrument": "XAUUSD",
            "bid": 2500.0,
            "ask": 2501.0
        }
        
        await manager._publish_callback(price_data)
        
        expected_channel = "market_data:tick:XAUUSD"
        expected_cache_key = "market_data:spot:XAUUSD"
        expected_mapping = {
            "bid": 2500.0,
            "ask": 2501.0,
            "ts": 123456789.0
        }
        
        publisher_instance.publish_with_cache.assert_called_once_with(
            expected_channel, expected_cache_key, price_data, expected_mapping
        )

@pytest.mark.asyncio
async def test_stream_manager_publish_callback_other_event():
    with patch("app.streaming.manager.RedisPublisher") as MockPublisher:
        publisher_instance = MockPublisher.return_value
        publisher_instance.publish = AsyncMock()
        publisher_instance.connect = AsyncMock()
        
        manager = StreamManager()
        manager.publisher = publisher_instance
        
        # Test non-PRICE event
        other_data = {
            "type": "heartbeat",
            "instrument": "XAUUSD"
        }
        
        await manager._publish_callback(other_data)
        
        expected_channel = "market_data:tick:XAUUSD"
        publisher_instance.publish.assert_called_once_with(expected_channel, other_data)
