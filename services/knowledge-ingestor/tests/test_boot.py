from fastapi.testclient import TestClient
from unittest.mock import patch


def test_app_import_and_initialization():
    """
    Cold Boot Test: Ensures the FastAPI app imports and initializes without NameErrors or crashes.
    """
    # Mock dependencies that might trigger on import or startup
    with (
        patch("app.core.orchestrator.TaskOrchestrator._get_redis"),
        patch("app.core.health.StartupGuard.check_redis", return_value=True),
        patch("app.core.health.StartupGuard.check_directories", return_value=True),
        patch("app.core.health.StartupGuard.check_llm_tiers", return_value={}),
    ):
        from app.api.main import app

        client = TestClient(app)

        # Test basic health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


def test_app_startup_events():
    """Verify that startup events register background tasks without crashing."""
    with (
        patch("app.core.orchestrator.TaskOrchestrator._get_redis"),
        patch("app.core.health.StartupGuard.check_redis", return_value=True),
        patch("app.core.health.StartupGuard.check_directories", return_value=True),
    ):
        from app.api.main import app

        with TestClient(app) as client:
            # Entering the context manager triggers the 'startup' event
            response = client.get("/health")
            assert response.status_code == 200
