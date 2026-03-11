
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.security import get_current_user
from app.models.user import User

def test_get_daily_briefing_success(client, mock_current_user):
    """
    Test successful retrieval of daily briefing.
    Uses mock for the downstream AI Analyst service interaction.
    """
    # Override get_current_user dependency
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user

    mock_briefing_data = {
        "report": "# Pre-Flight Checklist\n\n- **Status**: Go",
        "timestamp": "2024-01-01T12:00:00Z"
    }

    # Patch httpx.AsyncClient to return a mock that handles async context manager and async methods
    with patch("httpx.AsyncClient") as MockClient:
        mock_instance = MockClient.return_value
        
        # Setup Async Context Manager
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        
        # Setup Response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "data": mock_briefing_data}

        # Setup POST method as AsyncMock returning the response (Code calls client.post)
        mock_instance.post = AsyncMock(return_value=mock_response)

        # Execute
        response = client.get("/api/v1/ai/briefing", headers={"Authorization": "Bearer mock_token"})
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["content"] == mock_briefing_data["report"]

def test_get_daily_briefing_unauthorized(client):
    """
    Test unauthorized access.
    """
    from app.main import app
    app.dependency_overrides = {} # Clear overrides to force auth check
    
    response = client.get("/api/v1/ai/briefing")
    assert response.status_code == 401

def test_get_daily_briefing_service_unavailable(client, mock_current_user):
    """
    Test handling of downstream service failure.
    """
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user

    with patch("httpx.AsyncClient") as MockClient:
        mock_instance = MockClient.return_value
        
        # Setup Async Context Manager
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None

        # Setup Response
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"
        
        # Mock raise_for_status to raise exception
        def raise_http_error():
            import httpx
            request = httpx.Request("POST", "http://ai-service")
            raise httpx.HTTPStatusError("Service Unavailable", request=request, response=mock_response)
            
        mock_response.raise_for_status.side_effect = raise_http_error
        
        # Setup POST method as AsyncMock returning the response
        mock_instance.post = AsyncMock(return_value=mock_response)

        # Execute
        response = client.get("/api/v1/ai/briefing", headers={"Authorization": "Bearer mock_token"})
        
        # Expecting 503 from Gateway
        assert response.status_code == 503
