
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket
from app.streaming.manager import ConnectionManager

@pytest.fixture
def mock_redis():
    with patch("app.streaming.manager.RedisSubscriber") as mock:
        yield mock

@pytest.mark.asyncio
async def test_manager_connect_disconnect(mock_redis):
    manager = ConnectionManager()
    # Reset for test because it's a singleton
    manager.active_connections.clear()
    
    mock_ws = AsyncMock(spec=WebSocket)
    symbols = ["EUR_USD", "XAU_USD"]
    
    await manager.connect(mock_ws, symbols)
    
    assert mock_ws in manager.active_connections["EUR_USD"]
    assert mock_ws in manager.active_connections["XAU_USD"]
    assert mock_ws.accept.called
    
    await manager.disconnect(mock_ws, symbols)
    # Don't access the key directly as it recreates it in defaultdict
    # assert mock_ws not in manager.active_connections["EUR_USD"] 
    assert "EUR_USD" not in manager.active_connections # Should be cleaned up

@pytest.mark.asyncio
async def test_manager_broadcast(mock_redis):
    manager = ConnectionManager()
    manager.active_connections.clear()
    
    mock_ws1 = AsyncMock(spec=WebSocket)
    mock_ws2 = AsyncMock(spec=WebSocket)
    
    # Manually setup connections
    manager.active_connections["EUR_USD"].add(mock_ws1)
    manager.active_connections["EUR_USD"].add(mock_ws2)
    
    message = '{"price": 1.05}'
    await manager.broadcast("EUR_USD", message)
    
    mock_ws1.send_text.assert_awaited_with(message)
    mock_ws2.send_text.assert_awaited_with(message)

# TODO: Add test for _redis_listener if possible, but it requires mocking async generator
