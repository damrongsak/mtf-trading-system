
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.adapters.gateway import APIGatewayClient

@pytest.mark.asyncio
async def test_execute_signal_success():
    # Mock Response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "ord-123", "status": "executed"}
    
    # Mock httpx client
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        
        client = APIGatewayClient()
        payload = {"deployment_id": "dep-1", "symbol": "XAU/USD"}
        
        result = await client.execute_signal(payload)
        
        assert result == {"id": "ord-123", "status": "executed"}
        
        # Verify call args
        mock_post.assert_awaited_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"] == payload
        assert "x-internal-key" in kwargs["headers"]

@pytest.mark.asyncio
async def test_execute_signal_failure():
    # Mock Response
    mock_resp = AsyncMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Error"
    
    # Mock httpx client
    mock_post_fn = AsyncMock()
    mock_post_fn.return_value = mock_resp
    
    with patch("httpx.AsyncClient.post", side_effect=mock_post_fn):
        client = APIGatewayClient()
        result = await client.execute_signal({})
        
        assert result is None
