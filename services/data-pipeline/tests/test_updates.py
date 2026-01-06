import pytest
from app.streaming.publisher import RedisPublisher
from app.schemas import BackfillRequest
from app.utils.retry import async_retry
from datetime import datetime
from unittest.mock import AsyncMock, patch
import json

@pytest.mark.asyncio
async def test_redis_publisher_datetime_serialization():
    publisher = RedisPublisher()
    publisher.redis = AsyncMock()
    
    test_data = {
        "timestamp": datetime(2023, 1, 1, 12, 0, 0),
        "value": 100.5
    }
    
    await publisher.publish("test_channel", test_data)
    
    # Verify it was called with a stringified JSON
    args, _ = publisher.redis.publish.call_args
    channel, message = args
    
    assert channel == "test_channel"
    parsed_msg = json.loads(message)
    assert parsed_msg["timestamp"] == "2023-01-01 12:00:00"
    assert parsed_msg["value"] == 100.5

def test_backfill_request_validation():
    # Valid request
    req = BackfillRequest(
        symbol="XAU_USD",
        timeframe="H1",
        from_date="2023-01-01T00:00:00Z"
    )
    assert req.symbol == "XAU_USD"
    
    # Invalid symbol
    with pytest.raises(ValueError, match="Symbol must contain only uppercase letters"):
        BackfillRequest(symbol="xau_usd", timeframe="H1")
        
    # Invalid date
    with pytest.raises(ValueError, match="Date must be in ISO format"):
        BackfillRequest(symbol="XAU_USD", timeframe="H1", from_date="01-01-2023")

@pytest.mark.asyncio
async def test_async_retry_success():
    mock_func = AsyncMock(side_effect=[Exception("Fail"), Exception("Fail"), "Success"])
    
    @async_retry(max_retries=3, initial_delay=0.1)
    async def decorated_func():
        return await mock_func()
        
    result = await decorated_func()
    assert result == "Success"
    assert mock_func.call_count == 3

@pytest.mark.asyncio
async def test_async_retry_exhausted():
    mock_func = AsyncMock(side_effect=Exception("Permanent Fail"))
    
    @async_retry(max_retries=2, initial_delay=0.1)
    async def decorated_func():
        return await mock_func()
        
    with pytest.raises(Exception, match="Permanent Fail"):
        await decorated_func()
    assert mock_func.call_count == 3 # Initial + 2 retries
