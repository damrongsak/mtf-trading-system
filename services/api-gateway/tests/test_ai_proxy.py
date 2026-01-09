import pytest
from unittest.mock import patch, AsyncMock, Mock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.security import get_current_user
from app.database import get_db
import uuid

# Mock User and DB
mock_user = MagicMock()
mock_user.id = uuid.uuid4()
mock_user.email = "test@example.com"
mock_db = MagicMock()

def override_get_current_user():
    return mock_user

def override_get_db():
    try:
        yield mock_db
    finally:
        pass

app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture
def mock_ai_client():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        yield mock_get

def test_list_agents_proxy(mock_ai_client):
    # Mock successful response from AI Service
    from unittest.mock import Mock
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "success",
        "data": [
            {"id": "agent1", "name": "Agent 1", "status": "active"}
        ]
    }
    mock_response.raise_for_status = Mock()
    
    mock_ai_client.return_value = mock_response

    response = client.get("/api/v1/ai/agents")
    
    # Check that the proxy wraps it correctly
    assert response.status_code == 200
    data = response.json()
    # API Gateway wraps in success_response default structure? 
    # Current implementation wraps response.json().get("data") into success_response(data=...)
    # success_response adds {"status": "success", "data": ...}
    
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == "agent1"


def test_list_agents_proxy_error(mock_ai_client):
    # Mock error from AI Service
    from httpx import HTTPStatusError, Request, Response
    
    mock_response = AsyncMock()
    # When using side_effect with exception, mock_ai_client (the mock_get) raises it when awaited
    mock_ai_client.side_effect = HTTPStatusError("Error", request=Request("GET", "/"), response=Response(503, text="Service unavailable"))

    response = client.get("/api/v1/ai/agents")
    assert response.status_code == 503

@pytest.fixture
def mock_ai_post():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        yield mock_post

def test_analyze_market_proxy(mock_ai_post):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"insight": "Bullish trend detected", "timestamp": "2025-01-01T12:00:00Z"}
    mock_response.raise_for_status = Mock()
    mock_ai_post.return_value = mock_response

    response = client.post("/api/v1/ai/market-analysis", json={
        "trend_4h": "bullish", 
        "current_price": 2000.0,
        "key_levels": [],
        "recent_signals": []
    })
    assert response.status_code == 200
    assert response.json()["data"]["insight"] == "Bullish trend detected"

def test_analyze_journal_proxy(mock_ai_post):
    from unittest.mock import Mock
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"insight": "fomo", "timestamp": "2025"} 
    mock_response.raise_for_status = Mock()
    mock_ai_post.return_value = mock_response

    response = client.post("/api/v1/ai/journal-analysis", json={"entry_id": "123", "entry_content": "test"})
    assert response.status_code == 200
    assert response.json()["data"]["insight"] == "fomo"

def test_get_daily_briefing_proxy(mock_ai_post):
    from unittest.mock import Mock
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"report": "Market is up", "timestamp": "2025-01-01"}
    mock_response.raise_for_status = Mock()
    mock_ai_post.return_value = mock_response

    response = client.get("/api/v1/ai/briefing")
    assert response.status_code == 200
    assert response.json()["data"]["content"] == "Market is up"

def test_list_chat_sessions():
    mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = []
    response = client.get("/api/v1/ai/chat/sessions")
    assert response.status_code == 200
    assert response.json()["data"] == []

@patch("app.routers.ai.ChatSession")
@patch("app.routers.ai.ChatMessage")
def test_create_chat_session(mock_msg, mock_session):
    mock_db.add = Mock()
    mock_db.commit = Mock()
    mock_db.refresh = Mock()
    # Mock instance
    mock_session_inst = Mock()
    mock_session_inst.id = uuid.uuid4()
    mock_session_inst.title = "Test Chat"
    mock_session_inst.user_id = uuid.uuid4()
    mock_session_inst.strategy_id = uuid.uuid4()
    mock_session_inst.created_at = "2025-01-01T00:00:00Z"
    mock_session_inst.updated_at = "2025-01-01T00:00:00Z"
    mock_session.return_value = mock_session_inst
    
    response = client.post("/api/v1/ai/chat/sessions", json={"initial_message": "Hello"})
    assert response.status_code == 200
    assert "id" in response.json()["data"]


@patch("app.routers.ai.ChatSession")
@pytest.mark.skip(reason="SQLAlchemy registry conflict in tests")
def test_send_chat_message(mock_session_cls, mock_ai_post):
    # Mock Session finding
    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    mock_session.user_id = mock_user.id
    mock_session.strategy_id = None
    mock_session.title = "Test Chat"
    mock_session.created_at = "2025-01-01T00:00:00Z"
    mock_session.updated_at = "2025-01-01T00:00:00Z"
    mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_session
    
    # Mock AI response
    from unittest.mock import Mock
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "AI Reply"}
    mock_ai_post.return_value = mock_response

    response = client.post(f"/api/v1/ai/chat/sessions/{mock_session.id}/messages", json={"content": "Hi"})
    assert response.status_code == 200
    assert response.json()["data"]["content"] == "AI Reply"


