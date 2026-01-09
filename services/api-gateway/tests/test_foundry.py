import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.security import get_current_user
from app.models.user import User

@pytest.fixture
def mock_db_session():
    return MagicMock()

@pytest.fixture
def override_dependency(mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    yield
    app.dependency_overrides = {}

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = "user123"
    user.username = "testuser"
    return user

@pytest.fixture
def client(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides[get_current_user] = None

def test_assemble_strategy_success(client, override_dependency):
    with patch("httpx.Client") as MockClient:
        mock_instance = MockClient.return_value.__enter__.return_value
        mock_instance.post.return_value.status_code = 200
        mock_instance.post.return_value.json.return_value = {"pipeline_hash": "abc", "errors": []}
        
        payload = {"config": {"foo": "bar"}}
        response = client.post("/api/v1/foundry/assemble", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["pipeline_hash"] == "abc"

def test_assemble_strategy_core_error(client, override_dependency):
    with patch("httpx.Client") as MockClient:
        mock_instance = MockClient.return_value.__enter__.return_value
        mock_instance.post.return_value.status_code = 400
        mock_instance.post.return_value.text = "Bad Request"
        
        payload = {"config": {"foo": "bar"}}
        response = client.post("/api/v1/foundry/assemble", json=payload)
        
        # The router returns 200 OK but with status=error structure
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Bad Request" in data["data"]["errors"][0]

def test_validate_strategy_success(client, override_dependency):
    with patch("httpx.Client") as MockClient:
        mock_instance = MockClient.return_value.__enter__.return_value
        mock_instance.post.return_value.status_code = 200
        mock_instance.post.return_value.json.return_value = {
            "robustness_score": 90, 
            "avg_sharpe_test": 1.5,
            "details": []
        }
        
        payload = {
            "symbol": "XAU/USD",
            "timeframe": "1h",
            "start_date": "2023-01-01T00:00:00Z",
            "end_date": "2023-01-02T00:00:00Z",
            "config": {}
        }
        response = client.post("/api/v1/foundry/validate", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["robustness_score"] == 90

def test_validate_strategy_error(client, override_dependency):
    with patch("httpx.Client") as MockClient:
        mock_instance = MockClient.return_value.__enter__.return_value
        mock_instance.post.return_value.status_code = 400
        mock_instance.post.return_value.text = "Invalid Config"
        
        payload = {
            "symbol": "XAU/USD",
            "timeframe": "1h",
            "start_date": "2023-01-01T00:00:00Z",
            "end_date": "2023-01-02T00:00:00Z",
            "config": {}
        }
        # The router raises HTTPException for validate endpoint
        response = client.post("/api/v1/foundry/validate", json=payload)
        
        assert response.status_code == 400
        # Check if detail is present, or just text
        assert "Invalid Config" in response.text
