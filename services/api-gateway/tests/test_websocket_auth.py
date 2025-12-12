from fastapi.testclient import TestClient
from app.main import app
from app.security import create_access_token
import pytest
from unittest.mock import patch, AsyncMock

# Mock the strategy core connection to avoid external dependency failure
@pytest.fixture
def mock_websockets_connect():
    with patch("websockets.connect") as mock:
        mock_ws = AsyncMock()
        from fastapi import WebSocketDisconnect
        mock_ws.recv.side_effect = ['{"price": 1.2345}', WebSocketDisconnect()]
        mock_ws.close = AsyncMock()
        # Async context manager mock
        mock.return_value.__aenter__.return_value = mock_ws
        mock.return_value.__aexit__.return_value = None
        yield mock

def test_websocket_auth_success(mock_websockets_connect):
    client = TestClient(app)
    token = create_access_token(data={"sub": "testuser"})
    
    with client.websocket_connect(f"/api/v1/stream/prices?token={token}") as websocket:
        # If connection is accepted, we should be able to receive data (or at least not disconnect immediately with 403/1008)
        # Note: TestClient.websocket_connect sends initial handshake.
        # If it failed auth, it would raise WebSocketDisconnect or close with 1008.
        websocket.close()
        pass

def test_websocket_auth_failure():
    client = TestClient(app)
    # No token or invalid token
    with pytest.raises(Exception) as excinfo:
        with client.websocket_connect("/api/v1/stream/prices?token=invalid"):
             pass
    # Depending on client implementation, it might raise or just close.
    # Starlette TestClient raises WebSocketDisconnect usually for 403/close.
