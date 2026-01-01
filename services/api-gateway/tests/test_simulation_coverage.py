import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.routers.simulation import SimulationRequest

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_run_simulation_success(client):
    payload = {
        "regime": {"trend": "UPTREND", "volatility": 5, "noise": "GAUSSIAN"},
        "grid": {"step_size": 10.0, "grid_levels": 5, "initial_lot": 0.1, "use_compound": False, "stop_loss_pct": 2.0},
        "iterations": 10
    }
    
    mock_response_data = {
        "id": "sim_123",
        "metrics": {
            "total_pnl": 100.0,
            "win_rate": 0.6,
            "max_drawdown": 50.0,
            "sharpe_ratio": 1.5,
            "profit_factor": 2.0
        },
        "equity_curve": [{"timestamp": "2023-01-01", "value": 1000}],
        "status": "COMPLETED"
    }

    # Patch httpx.AsyncClient in app.routers.simulation
    with patch("app.routers.simulation.httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        mock_instance.post = AsyncMock()
        mock_instance.post.return_value.status_code = 200
        mock_instance.post.return_value.json = MagicMock(return_value=mock_response_data)
        
        response = client.post("/api/v1/simulation/", json=payload)
        
        if response.status_code != 200:
            print(f"DEBUG SIM: {response.json()}")
            
        assert response.status_code == 200
        assert response.json()["data"]["id"] == "sim_123"

def test_run_simulation_failure_upstream(client):
    payload = {
        "regime": {"trend": "UPTREND", "volatility": 5, "noise": "GAUSSIAN"},
        "grid": {"step_size": 10, "grid_levels": 5, "initial_lot": 0.1, "use_compound": False, "stop_loss_pct": 2.0}
    }
    
    with patch("app.routers.simulation.httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        mock_instance.post = AsyncMock()
        mock_instance.post.return_value.status_code = 500
        mock_instance.post.return_value.json = MagicMock(return_value={"detail": "Upstream error"})
        
        response = client.post("/api/v1/simulation/", json=payload)
        
        assert response.status_code == 500
        assert "Upstream error" in response.json()["message"]

def test_run_simulation_connection_error(client):
    payload = {
        "regime": {"trend": "UPTREND", "volatility": 5, "noise": "GAUSSIAN"},
        "grid": {"step_size": 10, "grid_levels": 5, "initial_lot": 0.1, "use_compound": False, "stop_loss_pct": 2.0}
    }
    
    with patch("app.routers.simulation.httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        mock_instance.post = AsyncMock()
        mock_instance.post.side_effect = Exception("Connection refused") # simulating httpx.RequestError logic (usually handled by catching RequestError)
        # Note: app logic catches httpx.RequestError. I should raise that.
        # But importing httpx in test file to raise it is cleaner.
        import httpx
        mock_instance.post.side_effect = httpx.RequestError("Connection refused")
        
        response = client.post("/api/v1/simulation/", json=payload)
        
        assert response.status_code == 503
        assert "Service unavailable" in response.json()["message"]
