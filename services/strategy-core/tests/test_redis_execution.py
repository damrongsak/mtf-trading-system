import pytest
import json
from unittest.mock import AsyncMock, patch
from app.adapters.execution import ExecutionClient

@pytest.fixture
def client():
    return ExecutionClient()

@pytest.mark.asyncio
async def test_place_order_success(client):
    order_data = {"symbol": "XAU_USD", "direction": "BUY"}
    
    with patch("app.adapters.execution.redis.from_url") as mock_redis_factory:
        mock_redis = AsyncMock()
        mock_redis_factory.return_value = mock_redis
        
        result = await client.place_order(order_data)
        
        assert result["status"] == "queued"
        mock_redis.lpush.assert_called_once()
        # Check that it serialized and pushed
        args = mock_redis.lpush.call_args[0]
        assert args[0] == "queue:execution:commands"
        assert json.loads(args[1]) == order_data

@pytest.mark.asyncio
async def test_place_order_redis_error(client):
    order_data = {"test": 1}
    
    with patch("app.adapters.execution.redis.from_url") as mock_redis_factory:
        mock_redis = AsyncMock()
        mock_redis.lpush.side_effect = Exception("Redis Down")
        mock_redis_factory.return_value = mock_redis
        
        with pytest.raises(Exception) as excinfo:
            await client.place_order(order_data)
        
        assert "Redis Down" in str(excinfo.value)
        assert client._redis is None # Connection should be cleared on error
