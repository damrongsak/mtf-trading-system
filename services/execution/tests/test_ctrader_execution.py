
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.adapters.ctrader import CTraderOrderAdapter
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
from ctrader_open_api.messages.OpenApiMessages_pb2 import *

# Mock the client module
@pytest.fixture
def mock_client():
    with patch("app.adapters.ctrader.AsyncCTraderClient") as MockClient:
        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.disconnect = AsyncMock()
        instance.authorize_app = AsyncMock(return_value=True)
        instance.authorize_account = AsyncMock(return_value=True)
        instance.send = AsyncMock()
        yield instance

@pytest.mark.asyncio
async def test_place_market_order_success(mock_client):
    adapter = CTraderOrderAdapter(
        client_id="test_id",
        client_secret="test_secret", 
        account_id="12345",
        token="test_token"
    )
    
    # Mock send to return success?
    # For MVP adapter, we just returned a stub dict. 
    # But later we will process ProtoOANewOrderRes.
    # Let's verify the auth flow happened.
    
    result = await adapter.place_market_order(
        symbol="XAU/USD",
        units=1000
    )
    
    assert adapter.client.connect.called
    adapter.client.authorize_app.assert_called_with("test_id", "test_secret")
    adapter.client.authorize_account.assert_called_with(12345, "test_token")
    assert result["status"] == "executed"
    
@pytest.mark.asyncio
async def test_get_account_summary(mock_client):
    adapter = CTraderOrderAdapter(
        client_id="test_id",
        client_secret="test_secret", 
        account_id="12345",
        token="test_token"
    )
    
    summary = await adapter.get_account_summary()
    
    assert summary["balance"] == "0"
    assert summary["openTradeCount"] == 0
