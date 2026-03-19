"""
Timeout/Retry Logic Tests

Tests for:
- T1: Broker Slow Response → Retry up to 3x
- T2: Network Timeout → Queue & retry on reconnect
- T3: Idempotent Retry → No double execution
- T4: Max Retries Exceeded → Clear error, dead letter queue
- T5: Concurrent Requests → Handle race conditions

SAFETY NOTICE:
    - Uses unittest.mock (AsyncMock/MagicMock)
    - NO real broker connections
    - NO real orders placed
"""
import pytest
import json
import asyncio
from unittest.mock import AsyncMock, patch
from app.worker import ExecutionWorker


# --- Fixtures ---

@pytest.fixture
def worker():
    """Create a fresh ExecutionWorker instance."""
    w = ExecutionWorker()
    w.redis = None
    return w


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)  # No kill switch
    r.set = AsyncMock(return_value=True)  # Idempotency key set
    r.delete = AsyncMock()
    r.lpush = AsyncMock()
    r.brpop = AsyncMock()
    return r


@pytest.fixture
def sample_order():
    """Sample order request data."""
    return {
        "type": "OPEN",
        "symbol": "XAU_USD",
        "direction": "BUY",
        "volume": 0.01,
        "client_order_id": "test_order_001",
        "entry_price": 5280.0,
        "stop_loss": 5260.0,
        "take_profit": 5345.0
    }


# ============================================================================
# T1: Broker Slow Response → Retry up to 3x
# ============================================================================

@pytest.mark.asyncio
async def test_retry_on_broker_timeout(worker, mock_redis, sample_order):
    """
    [T1] When broker times out, retry up to 3 times before dead letter.
    Expected: Failed order is pushed back to queue for retry.
    Note: retry_count < 3 means retry (so retry_count=0,1,2 retry, 3+ goes to DLQ)
    """
    worker.redis = mock_redis
    
    with patch("app.worker.OrderService.execute_smart_order") as mock_execute:
        mock_execute.side_effect = TimeoutError("Broker timeout")
        
        with patch("app.worker.AsyncSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock()
            
            # Process the order (first attempt - fails, retry_count=0 -> 1)
            await worker._process_command("queue:execution:commands", json.dumps(sample_order))
            
            # Should have pushed retry message to queue
            assert mock_redis.lpush.call_count >= 1
            
            # Verify retry_count is incremented to 1
            pushed_messages = [call[0][1] for call in mock_redis.lpush.call_args_list]
            retry_msg = json.loads(pushed_messages[0])
            assert retry_msg.get("retry_count") == 1
            
            # Now simulate processing the retry (2nd attempt - retry_count=1 -> 2)
            mock_redis.lpush.reset_mock()
            await worker._process_command("queue:execution:commands", json.dumps(retry_msg))
            
            pushed_messages_2 = [call[0][1] for call in mock_redis.lpush.call_args_list]
            retry_msg_2 = json.loads(pushed_messages_2[0])
            assert retry_msg_2.get("retry_count") == 2
            
            # Simulate 3rd attempt (retry_count=2 -> 3, still retries!)
            mock_redis.lpush.reset_mock()
            await worker._process_command("queue:execution:commands", json.dumps(retry_msg_2))
            
            pushed_messages_3 = [call[0][1] for call in mock_redis.lpush.call_args_list]
            retry_msg_3 = json.loads(pushed_messages_3[0])
            assert retry_msg_3.get("retry_count") == 3
            
            # Now should go to DLQ (retry_count=3 -> exceeds limit)
            mock_redis.lpush.reset_mock()
            await worker._process_command("queue:execution:commands", json.dumps(retry_msg_3))
            
            dlq_calls = [call for call in mock_redis.lpush.call_args_list 
                         if call[0][0] == "queue:exec:dead"]
            assert len(dlq_calls) > 0, "Should move to DLQ after 3+ retry attempts"


@pytest.mark.asyncio
async def test_retry_respects_max_attempts(worker, mock_redis, sample_order):
    """
    [T4] After max retries (3), order goes to dead letter queue.
    When retry_count >= 3, order should go to DLQ instead of retrying again.
    Note: Code checks `retry_count < 3` for retry, so retry_count=3+ goes to DLQ.
    """
    worker.redis = mock_redis
    
    with patch("app.worker.OrderService.execute_smart_order") as mock_execute:
        mock_execute.side_effect = Exception("Persistent failure")
        
        with patch("app.worker.AsyncSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock()
            
            # Simulate retry_count=3 (already exceeded limit)
            sample_order["retry_count"] = 3
            
            # Process should move to DLQ after max retries
            await worker._process_command("queue:execution:commands", json.dumps(sample_order))
            
            # Should push to dead letter queue (queue:exec:dead)
            dlq_calls = [call for call in mock_redis.lpush.call_args_list 
                         if call[0][0] == "queue:exec:dead"]
            assert len(dlq_calls) > 0, "Order should go to DLQ when retry_count >= 3"
            
            # Verify the DLQ message contains the error
            dlq_msg = json.loads(dlq_calls[0][0][1])
            assert dlq_msg.get("last_error") == "Persistent failure"


# ============================================================================
# T2: Network Timeout → Queue & Retry on Reconnect
# ============================================================================

@pytest.mark.asyncio
async def test_redis_connection_error_triggers_reconnect(worker, sample_order):
    """
    [T2] When Redis connection fails, worker should handle gracefully.
    """
    # Simulate Redis connection error in brpop
    with patch("app.worker.redis.from_url") as mock_redis_factory:
        mock_redis = AsyncMock()
        mock_redis.brpop.side_effect = [
            Exception("Connection refused"),
            ("queue:execution:commands", json.dumps(sample_order)),
            asyncio.CancelledError()
        ]
        mock_redis_factory.return_value = mock_redis
        
        worker.redis_url = "redis://localhost:6379"
        
        # Should not crash, should retry connection
        task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.1)
        worker._running = False
        
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        
        # Should have attempted to reconnect
        assert mock_redis_factory.call_count >= 1


# ============================================================================
# T3: Idempotent Retry → No Double Execution
# ============================================================================

@pytest.mark.asyncio
async def test_idempotency_prevents_duplicate_execution(worker, mock_redis, sample_order):
    """
    [T3] Same client_order_id should not execute twice (idempotency key).
    """
    worker.redis = mock_redis
    
    # Simulate idempotency key already exists (duplicate order)
    mock_redis.set = AsyncMock(return_value=False)  # Key exists
    
    with patch("app.worker.OrderService.execute_smart_order") as mock_execute:
        with patch("app.worker.AsyncSessionLocal"):
            await worker._process_command("queue:execution:commands", json.dumps(sample_order))
            
            # Should NOT execute order (duplicate rejected)
            mock_execute.assert_not_called()
            
            # Should log warning about duplicate
            # (would need to verify logger call in real test)


@pytest.mark.asyncio
async def test_idempotency_key_released_on_biz_error(worker, mock_redis, sample_order):
    """
    [T3] When biz logic error occurs, release idempotency key so retry can proceed.
    """
    worker.redis = mock_redis
    
    with patch("app.worker.OrderService.execute_smart_order") as mock_execute:
        mock_execute.side_effect = ValueError("Invalid order parameters")
        
        with patch("app.worker.AsyncSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock()
            
            await worker._process_command("queue:execution:commands", json.dumps(sample_order))
            
            # Should release the lock for retry
            mock_redis.delete.assert_called_once()
            delete_key = mock_redis.delete.call_args[0][0]
            assert "processed_order" in delete_key


# ============================================================================
# T5: Concurrent Requests → Handle Race Conditions
# ============================================================================

@pytest.mark.asyncio
async def test_concurrent_orders_same_symbol(worker, mock_redis, sample_order):
    """
    [T5] Multiple concurrent orders for same symbol should all process correctly.
    """
    worker.redis = mock_redis
    
    # Different client_order_ids for concurrent orders
    orders = [
        {**sample_order, "client_order_id": "concurrent_001"},
        {**sample_order, "client_order_id": "concurrent_002"},
        {**sample_order, "client_order_id": "concurrent_003"},
    ]
    
    with patch("app.worker.OrderService.execute_smart_order") as mock_execute:
        mock_execute.return_value = {"id": "order_123"}
        
        with patch("app.worker.AsyncSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock()
            
            # Process all orders concurrently
            tasks = [
                worker._process_command("queue:execution:commands", json.dumps(order))
                for order in orders
            ]
            await asyncio.gather(*tasks)
            
            # All orders should be executed
            assert mock_execute.call_count == 3


@pytest.mark.asyncio
async def test_concurrent_retry_and_new_order(worker, mock_redis, sample_order):
    """
    [T5] New order arriving while retry is in progress should not block.
    """
    worker.redis = mock_redis
    
    # Track execution order
    execution_log = []
    
    async def slow_execute(req_data, db):
        execution_log.append(f"start_{req_data.get('client_order_id')}")
        await asyncio.sleep(0.1)  # Simulate slow broker
        execution_log.append(f"end_{req_data.get('client_order_id')}")
        return {"id": "order_123"}
    
    with patch("app.worker.OrderService.execute_smart_order", side_effect=slow_execute):
        with patch("app.worker.AsyncSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock()
            
            # Start first order (will be slow)
            task1 = worker._process_command("queue:execution:commands", json.dumps(sample_order))
            
            # Start second order while first is still processing
            sample_order2 = {**sample_order, "client_order_id": "order_002"}
            task2 = worker._process_command("queue:execution:commands", json.dumps(sample_order2))
            
            await asyncio.gather(task1, task2)
            
            # Both should complete (concurrent processing)
            assert len(execution_log) == 4  # 2 starts + 2 ends


# ============================================================================
# Error Handling & Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_invalid_json_handled_gracefully(worker, mock_redis):
    """
    Invalid JSON in queue should not crash worker.
    """
    worker.redis = mock_redis
    
    # Process invalid JSON
    await worker._process_command("queue:execution:commands", "not valid json{{{")
    
    # Should log error, not crash
    # (would verify logger.error call in real test with patch)


@pytest.mark.asyncio
async def test_kill_switch_blocks_new_orders(worker, mock_redis, sample_order):
    """
    When global kill switch is ON, new OPEN orders should be rejected.
    """
    mock_redis.get = AsyncMock(return_value="1")  # Kill switch ON
    worker.redis = mock_redis
    
    with patch("app.worker.OrderService.execute_smart_order") as mock_execute:
        with patch("app.worker.AsyncSessionLocal"):
            await worker._process_command("queue:execution:commands", json.dumps(sample_order))
            
            # Should NOT execute (blocked by kill switch)
            mock_execute.assert_not_called()


@pytest.mark.asyncio
async def test_kill_switch_allows_close_orders(worker, mock_redis):
    """
    CLOSE orders should still work even when kill switch is ON.
    """
    mock_redis.get = AsyncMock(return_value="1")  # Kill switch ON
    worker.redis = mock_redis
    
    close_order = {
        "type": "CLOSE",
        "symbol": "XAU_USD",
        "trade_id": "12345",
        "client_order_id": "close_001"
    }
    
    with patch("app.worker.OrderService.execute_smart_order") as mock_execute:
        mock_execute.return_value = {"id": "close_123"}
        
        with patch("app.worker.AsyncSessionLocal"):
            await worker._process_command("queue:execution:commands", json.dumps(close_order))
            
            # Should execute (CLOSE allowed during kill switch)
            mock_execute.assert_called_once()
