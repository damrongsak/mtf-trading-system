import pytest
import json
import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.api.main import app
from app.core.orchestrator import orchestrator


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_orchestrator():
    """Mock the global orchestrator instance."""
    with patch("app.api.main.orchestrator") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_search_cache():
    """Mock WebSearch cache globally for these tests."""
    with patch("app.tools.web_search.get_cache_region") as mock:
        region = mock.return_value
        from dogpile.cache.api import NO_VALUE

        region.get.return_value = NO_VALUE
        yield region


@pytest.fixture
def mock_orch_redis():
    """Mock the orchestrator's Redis internally."""
    with patch.object(orchestrator, "_get_redis") as mock:
        r = mock.return_value
        r.smembers.return_value = {"task-1", "task-2"}
        r.get.side_effect = lambda k: {
            "task:task-1": json.dumps(
                {
                    "task_id": "task-1",
                    "status": "completed",
                    "result": {"total_nodes": 5},
                }
            ),
            "task:task-2": json.dumps(
                {"task_id": "task-2", "status": "failed", "error": "timeout"}
            ),
        }.get(k if isinstance(k, str) else k.decode())
        r.keys.return_value = ["task:task-1", "task:task-2"]
        yield r


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_ingest_directory_success(client, mock_orchestrator):
    """Test standard directory ingestion."""
    mock_orchestrator.register_task = AsyncMock(
        side_effect=lambda fn, batch_id=None: f"task-{uuid.uuid4()}"
    )

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.glob") as mock_glob,
    ):
        f1 = MagicMock(spec=Path)
        f1.is_file.return_value = True
        f1.suffix = ".md"
        f1.name = "test1.md"

        f2 = MagicMock(spec=Path)
        f2.is_file.return_value = True
        f2.suffix = ".pdf"
        f2.name = "test2.pdf"

        mock_glob.return_value = [f1, f2]

        with patch("app.api.main.get_ingestor"):
            response = client.post(
                "/ingest/directory", json={"path": "/tmp/test", "force": False}
            )

            assert response.status_code == 202
            data = response.json()
            assert "batch_id" in data
            assert data["total_files"] == 2
            assert len(data["tasks"]) == 2


@pytest.mark.asyncio
async def test_ingest_url_success(client, mock_orchestrator):
    """Test URL ingestion trigger."""
    target_url = "https://example.com/macro"
    mock_orchestrator.register_task = AsyncMock(return_value="task-123")

    response = client.post("/ingest/url", json={"url": target_url})

    assert response.status_code == 202
    assert response.json()["task_id"] == "task-123"


def test_get_stats(client, mock_orchestrator):
    """Test global stats endpoint."""
    mock_orchestrator.get_global_stats.return_value = {
        "global": {"total_tasks_last_24h": 5},
        "statuses": {"completed": 3, "failed": 2},
    }

    response = client.get("/stats")
    assert response.status_code == 200
    assert response.json()["global"]["total_tasks_last_24h"] == 5


def test_list_tasks(client, mock_orch_redis):
    """Test the list tasks endpoint."""
    response = client.get("/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 2
    assert tasks[0]["task_id"] == "task-1"


def test_batch_status_endpoint(mock_orch_redis, client):
    """Verify batch-level statistics."""
    batch_id = "batch-123"
    # Ensure smembers returns strings as strings or bytes if the mock handles it
    mock_orch_redis.smembers.return_value = {"task-1", "task-2"}

    response = client.get(f"/batch/{batch_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["batch_id"] == batch_id
    assert data["total"] == 2
    assert data["nodes_created"] == 5
    assert len(data["tasks"]) == 2


def test_task_status_not_found(mock_orch_redis, client):
    """Verify 404 for non-existent tasks."""
    mock_orch_redis.get.return_value = None

    response = client.get("/status/missing-task")
    assert response.status_code == 404


def test_batch_not_found(mock_orch_redis, client):
    """Verify 404 for missing batches."""
    # Orchestrator returns total=0 and status="not_found" when smembers is empty
    mock_orch_redis.smembers.return_value = set()

    response = client.get("/batch/non-existent-batch")
    assert response.status_code == 404
    assert response.json()["detail"] == "Batch not found"
