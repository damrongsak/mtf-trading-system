import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.streaming.client import RedisStreamClient
from app.streaming.consumers import MarketFeatureConsumer

@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    # Mock context manager for from_url
    with patch('redis.asyncio.from_url', return_value=mock) as p:
        yield mock

@pytest.mark.asyncio
async def test_client_connect_creates_group(mock_redis):
    client = RedisStreamClient("redis://test", "test_stream", "test_group", "test_consumer")
    
    await client.connect()
    
    mock_redis.xgroup_create.assert_called_once_with(
        "test_stream", "test_group", id="$", mkstream=True
    )
    assert client.running is True

@pytest.mark.asyncio
async def test_consumer_parses_features(mock_redis):
    consumer = MarketFeatureConsumer("redis://test")
    
    # Mock stream data
    # format: [[stream_name, [[message_id, {field: value}]]]]
    mock_stream_data = [
        [
            "market.alpha.stream",
            [
                ("msg_1", {
                    "event_type": "features_calculated",
                    "features": '{"rsi_14": 30.5, "symbol": "BTC_USD"}',
                    "symbol": "BTC_USD"
                })
            ]
        ]
    ]
    
    # Mock xreadgroup to return data once, then empty (simulate loop)
    # We need to stop the loop, so we can raise CancelledError or just set running=False after first consumption if possible.
    # The client.consume() allows infinite loop.
    # We can mock consume() or just test the logic inside if we extract it, but client.consume yields.
    
    mock_redis.xreadgroup.side_effect = [mock_stream_data, asyncio.CancelledError()]
    
    handler_mock = AsyncMock()
    consumer.register_handler(handler_mock)
    
    await consumer.connect()
    
    # Run the consume loop
    # We use explicit iteration to verify behavior without infinite loop
    iterator = consumer.consume()
    
    try:
        async for msg_id, data in iterator:
            # We must verify that consumer logic (parsing) is working.
            # But 'consume' is in the base client, it just yields raw data.
            # The 'start' method in Consumer is what does the parsing.
            pass
    except asyncio.CancelledError:
        pass
        
    # Let's test the `start` method logic which loops over consume()
    # We need to patch consume to return our items
    
    with patch.object(RedisStreamClient, 'consume') as mock_consume:
        mock_consume.return_value.__aiter__.return_value = [
            ("msg_1", {
                "event_type": "features_calculated",
                "features": '{"rsi_14": 30.5, "symbol": "BTC_USD"}'
            })
        ]
        
        await consumer.start()
        
        # Verify handler called
        handler_mock.assert_called_once()
        args = handler_mock.call_args[0][0]
        assert args['rsi_14'] == 30.5
        assert args['symbol'] == "BTC_USD"
        
        # Verify Ack
        mock_redis.xack.assert_called_once_with("market.alpha.stream", "ai_analyst_group", "msg_1")
