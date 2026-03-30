import asyncio
import json
import pytest
import uuid
from unittest.mock import patch
from app.core.orchestrator import TaskOrchestrator
from app.core.app_config import config


@pytest.fixture
def mock_redis():
    with patch("redis.Redis") as mock:
        client = mock.return_value
        client.get.return_value = None
        client.set.return_value = True
        client.smembers.return_value = set()
        yield client


@pytest.mark.asyncio
async def test_register_task_no_batch(mock_redis):
    orchestrator = TaskOrchestrator()
    # Mock falkordb_client to return our mock_redis
    with patch.object(orchestrator, "_get_redis", return_value=mock_redis):
        task_id = await orchestrator.register_task("test.pdf")

        assert isinstance(uuid.UUID(task_id), uuid.UUID)
        assert mock_redis.set.called
        args, kwargs = mock_redis.set.call_args
        payload = json.loads(args[1])
        assert payload["filename"] == "test.pdf"
        assert payload["status"] == "queued"


@pytest.mark.asyncio
async def test_register_task_with_batch(mock_redis):
    orchestrator = TaskOrchestrator()
    batch_id = "batch-123"
    with patch.object(orchestrator, "_get_redis", return_value=mock_redis):
        task_id = await orchestrator.register_task("test.pdf", batch_id=batch_id)

        # Verify batch set addition
        mock_redis.sadd.assert_called_with(f"batch:{batch_id}", task_id)
        mock_redis.expire.assert_called_with(f"batch:{batch_id}", 86400)


@pytest.mark.asyncio
async def test_update_progress(mock_redis):
    orchestrator = TaskOrchestrator()
    task_id = "task-123"
    initial_payload = json.dumps({"task_id": task_id, "status": "queued"})
    mock_redis.get.return_value = initial_payload

    with patch.object(orchestrator, "_get_redis", return_value=mock_redis):
        await orchestrator.update_progress(
            task_id, stage="tier1_summary", detail="Thinking...", percentage=25.0
        )

        # Verify Redis update
        assert mock_redis.set.called
        # Verify SSE publish
        mock_redis.publish.assert_called()
        pub_args = json.loads(mock_redis.publish.call_args[0][1])
        assert pub_args["stage"] == "tier1_summary"
        assert pub_args["percentage"] == 25.0


@pytest.mark.asyncio
async def test_semaphore_concurrency(mock_redis):
    """Verify that only N tasks run concurrently."""
    # Temporarily set max concurrency to 2
    with patch.object(config, "ki_max_concurrency", 2):
        orchestrator = TaskOrchestrator()
        # Initialize semaphore since it's lazy
        orchestrator._semaphore = asyncio.BoundedSemaphore(2)

        active_tasks = 0
        max_seen_concurrency = 0

        async def mock_work(tid):
            nonlocal active_tasks, max_seen_concurrency
            active_tasks += 1
            max_seen_concurrency = max(max_seen_concurrency, active_tasks)
            await asyncio.sleep(0.1)  # Simulate slow work
            active_tasks -= 1

        with patch.object(orchestrator, "_get_redis", return_value=mock_redis):
            # Launch 5 tasks
            tasks = [orchestrator.run_managed(f"task-{i}", mock_work) for i in range(5)]
            await asyncio.gather(*tasks)

            # Max concurrency should have been 2
            assert max_seen_concurrency == 2


@pytest.mark.asyncio
async def test_finalize_task_success(mock_redis):
    orchestrator = TaskOrchestrator()
    task_id = "task-123"
    mock_redis.get.return_value = json.dumps({"task_id": task_id})

    with patch.object(orchestrator, "_get_redis", return_value=mock_redis):
        await orchestrator.finalize_task(
            task_id, status="completed", result={"nodes": 10}
        )

        args, _ = mock_redis.set.call_args
        payload = json.loads(args[1])
        assert payload["status"] == "completed"
        assert payload["stage"] == "pipeline_done"
        assert payload["result"]["nodes"] == 10


@pytest.mark.asyncio
async def test_get_batch_stats(mock_redis):
    orchestrator = TaskOrchestrator()
    batch_id = "batch-123"
    mock_redis.smembers.return_value = {"task-1", "task-2"}
    # Mock task data: one completed, one failed
    mock_redis.get.side_effect = [
        json.dumps({"status": "completed", "result": {"total_nodes": 5}}),
        json.dumps({"status": "failed", "error": "timeout"}),
    ]

    with patch.object(orchestrator, "_get_redis", return_value=mock_redis):
        stats = orchestrator.get_batch_stats(batch_id)

        assert stats["total"] == 2
        assert stats["completed"] == 1
        assert stats["failed"] == 1
        assert stats["nodes_created"] == 5


@pytest.mark.asyncio
async def test_global_stats(mock_redis):
    orchestrator = TaskOrchestrator()
    mock_redis.keys.return_value = ["task:1", "task:2"]
    mock_redis.get.side_effect = [
        json.dumps({"status": "completed"}),
        json.dumps({"status": "processing"}),
    ]

    with patch.object(orchestrator, "_get_redis", return_value=mock_redis):
        stats = orchestrator.get_global_stats()
        assert stats["global"]["total_tasks_last_24h"] == 2
        assert stats["statuses"]["completed"] == 1
        assert stats["statuses"]["processing"] == 1
