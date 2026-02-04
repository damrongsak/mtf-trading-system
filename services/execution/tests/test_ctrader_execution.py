
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.adapters.ctrader import CTraderOrderAdapter
# We need to mock the Proto objects since we can't easily instantiate them without the library context sometimes,
# but let's try to use generic Mocks for the response structure.

@pytest.fixture
def mock_client():
    with patch("app.adapters.ctrader.AsyncCTraderClient") as MockClient:
        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.disconnect = AsyncMock()
        instance.authorize_app = AsyncMock(return_value=True)
        instance.authorize_account = AsyncMock(return_value=True)
        instance.create_order = AsyncMock()
        instance.get_reconcile = AsyncMock()
        yield instance

@pytest.fixture
def adapter(mock_client):
    return CTraderOrderAdapter(
        client_id="test_id",
        client_secret="test_secret", 
        account_id="12345",
        token="test_token"
    )

@pytest.mark.asyncio
async def test_place_market_order_with_comment(adapter, mock_client):
    # Setup Mock Response for create_order
    mock_response = MagicMock()
    mock_response.HasField.side_effect = lambda field: field in ["deal", "order"]
    
    # Mock nested objects
    mock_response.deal.positionId = 123456
    mock_response.deal.executionPrice = 1.2345
    mock_response.order.orderId = 789012
    
    mock_client.create_order.return_value = mock_response
    
    # Mock symbol resolution
    adapter._resolve_symbol_id = AsyncMock(return_value=1001)

    result = await adapter.place_market_order(
        symbol="XAU/USD",
        units=1,
        comment="MarketOrderTest"
    )
    
    # Check if comment was passed
    mock_client.create_order.assert_called_once()
    call_kwargs = mock_client.create_order.call_args.kwargs
    assert call_kwargs["comment"] == "MarketOrderTest"
    assert call_kwargs["symbol_id"] == 1001
    
    # Check Return Structure (Oanda style)
    assert "orderFillTransaction" in result
    assert result["orderFillTransaction"]["id"] == "789012" # order_id preferred over position_id if present? logic says order_id or position_id
    # check logic: "id": order_id or position_id. order_id is obtained from res.order.orderId.
    assert result["orderFillTransaction"]["instrument"] == "XAU/USD"
    assert result["orderFillTransaction"]["units"] == "1"
    assert result["orderFillTransaction"]["price"] == "1.2345"

@pytest.mark.asyncio
async def test_place_limit_order_with_comment(adapter, mock_client):
    # Setup Mock Response for create_order
    mock_response = MagicMock()
    mock_response.HasField.side_effect = lambda field: field == "order"
    
    # Mock nested objects
    mock_response.order.orderId = 555555
    
    mock_client.create_order.return_value = mock_response
    
    # Mock symbol resolution
    adapter._resolve_symbol_id = AsyncMock(return_value=1002)

    result = await adapter.place_limit_order(
        symbol="EUR/USD",
        units=10,
        entry_price=1.1000,
        comment="LimitOrderTest"
    )
    
    # Check if comment was passed
    mock_client.create_order.assert_called_once()
    call_kwargs = mock_client.create_order.call_args.kwargs
    assert call_kwargs["comment"] == "LimitOrderTest"
    assert call_kwargs["price"] == 1.1000
    
    # Check Return Structure
    assert "orderCreateTransaction" in result
    assert result["orderCreateTransaction"]["id"] == "555555"
    assert result["orderCreateTransaction"]["instrument"] == "EUR/USD"
    assert result["orderCreateTransaction"]["price"] == "1.1"

@pytest.mark.asyncio
async def test_place_order_default_comment(adapter, mock_client):
    # Test default comment logic
    mock_response = MagicMock()
    mock_response.HasField.return_value = True
    mock_response.order.orderId = 111
    mock_response.deal.positionId = 222
    mock_response.deal.executionPrice = 1.0
    mock_client.create_order.return_value = mock_response
    adapter._resolve_symbol_id = AsyncMock(return_value=1001)
    
    await adapter.place_market_order("S", 1, trade_id="T123")
    
    call_kwargs = mock_client.create_order.call_args.kwargs
    # Logic: comment if comment else (f"Ref:{trade_id}" if trade_id else "Auto")
    assert call_kwargs["comment"] == "Ref:T123"

@pytest.mark.asyncio
async def test_place_order_auto_comment(adapter, mock_client):
    # Test auto comment logic
    mock_response = MagicMock()
    mock_response.HasField.return_value = True
    mock_response.order.orderId = 111
    mock_client.create_order.return_value = mock_response
    adapter._resolve_symbol_id = AsyncMock(return_value=1001)
    
    await adapter.place_market_order("S", 1)
    
    call_kwargs = mock_client.create_order.call_args.kwargs
    assert call_kwargs["comment"] == "Auto"
