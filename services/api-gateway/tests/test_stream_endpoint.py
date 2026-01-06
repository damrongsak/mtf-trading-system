
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, AsyncMock
import pytest

@patch("app.streaming.manager.stream_manager.connect", new_callable=AsyncMock)
@patch("app.streaming.manager.stream_manager.disconnect", new_callable=AsyncMock)
def test_websocket_endpoint(mock_disconnect, mock_connect):
    client = TestClient(app)
    
    # Mock auth token
    with patch("jose.jwt.decode") as mock_jwt:
        mock_jwt.return_value = {"sub": "testuser"}
        
        with client.websocket_connect("/api/v1/stream/prices?token=valid_token&symbols=EUR_USD") as websocket:
            # We expect connect to be called
            mock_connect.assert_called()
            # args are (websocket, ['EUR_USD'])
            # We can't easily assert websocket instance equality, but we can check symbols
            assert mock_connect.call_args[0][1] == ["EUR_USD"]
            
            # Close connection
            websocket.close()
        
        # We expect disconnect to be called after close
        mock_disconnect.assert_called()
