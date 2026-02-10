import pytest
import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.worker import ExecutionWorker

@pytest.fixture
def worker():
    return ExecutionWorker()

@pytest.mark.asyncio
async def test_worker_process_command_success(worker):
    message = json.dumps({"symbol": "XAU_USD", "direction": "BUY"})
    
    with patch("app.worker.AsyncSessionLocal") as mock_session_cls, \
         patch("app.worker.OrderService.execute_smart_order", new_callable=AsyncMock) as mock_execute:
        
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        mock_execute.return_value = {"id": "test_order_id"}
        
        await worker._process_command(message)
        
        mock_execute.assert_called_once()
        # Verify it was called with the dict from json
        args = mock_execute.call_args[0]
        assert args[0] == {"symbol": "XAU_USD", "direction": "BUY"}

@pytest.mark.asyncio
async def test_worker_process_command_invalid_json(worker):
    message = "invalid json"
    
    with patch("app.worker.logger") as mock_logger:
        await worker._process_command(message)
        mock_logger.error.assert_called()
        assert "Invalid JSON" in mock_logger.error.call_args[0][0]

@pytest.mark.asyncio
async def test_worker_lifecycle(worker):
    worker.redis_url = "redis://localhost"
    
    with patch("app.worker.redis.from_url") as mock_redis_factory:
        mock_redis = AsyncMock()
        mock_redis_factory.return_value = mock_redis
        
        # Mock brpop to return something then raise an error to break the loop
        mock_redis.brpop.side_effect = [
            ("queue", '{"test": 1}'),
            asyncio.CancelledError()
        ]
        
        # Run start in a task and cancel it soon
        task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.05)
        worker._running = False
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass
        
        assert mock_redis.brpop.called
        await worker.stop()
        mock_redis.close.assert_called()
