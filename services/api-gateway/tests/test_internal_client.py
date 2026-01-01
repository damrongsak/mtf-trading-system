import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.internal_client import StrategyClient, ExecutionClient

@pytest.fixture
def mock_httpx_client():
    with patch("httpx.AsyncClient") as mock:
        # Create a mock client instance that will be returned by __aenter__
        client_instance = AsyncMock()
        mock.return_value.__aenter__.return_value = client_instance
        yield client_instance

@pytest.mark.asyncio
async def test_run_backtest(mock_httpx_client):
    client = StrategyClient()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_httpx_client.post.return_value = mock_response
    
    result = await client.run_backtest({"data": "test"})
    
    assert result == {"status": "success"}
    mock_httpx_client.post.assert_called_once()
    args, kwargs = mock_httpx_client.post.call_args
    assert "/api/v1/backtest" in args[0]
    assert kwargs["json"] == {"data": "test"}

@pytest.mark.asyncio
async def test_start_strategy(mock_httpx_client):
    client = StrategyClient()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "123"}
    mock_httpx_client.post.return_value = mock_response
    
    result = await client.start_strategy("123", {"conf": 1})
    
    assert result == {"id": "123"}
    # assert url path contains /strategies/123/start
    args, _ = mock_httpx_client.post.call_args
    assert "/strategies/123/start" in args[0]

@pytest.mark.asyncio
async def test_run_custom_backtest(mock_httpx_client):
    client = StrategyClient()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_httpx_client.post.return_value = mock_response
    
    result = await client.run_custom_backtest({"data": "test"})
    assert result == {"status": "success"}
    args, _ = mock_httpx_client.post.call_args
    assert "/backtest/custom" in args[0]

@pytest.mark.asyncio
async def test_run_optimization(mock_httpx_client):
    client = StrategyClient()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"opt": "res"}
    mock_httpx_client.post.return_value = mock_response
    
    result = await client.run_optimization({"conf": 1})
    assert result == {"opt": "res"}
    args, _ = mock_httpx_client.post.call_args
    assert "/backtest/optimize" in args[0]

@pytest.mark.asyncio
async def test_run_monte_carlo(mock_httpx_client):
    client = StrategyClient()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"mc": "res"}
    mock_httpx_client.post.return_value = mock_response
    
    result = await client.run_monte_carlo({"conf": 1})
    assert result == {"mc": "res"}
    args, _ = mock_httpx_client.post.call_args
    assert "/backtest/monte-carlo" in args[0]

@pytest.mark.asyncio
async def test_stop_strategy(mock_httpx_client):
    client = StrategyClient()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "123", "status": "stopped"}
    mock_httpx_client.post.return_value = mock_response
    
    result = await client.stop_strategy("123")
    assert result == {"id": "123", "status": "stopped"}
    args, _ = mock_httpx_client.post.call_args
    assert "/strategies/123/stop" in args[0]

@pytest.mark.asyncio
async def test_close_trade(mock_httpx_client):
    client = ExecutionClient()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {"closed": True}}
    mock_httpx_client.post.return_value = mock_response
    
    result = await client.close_trade("t1", {"k":"v"})
    assert result == {"closed": True}
    args, kwargs = mock_httpx_client.post.call_args
    assert "/trades/close" in args[0]
    assert kwargs["json"]["broker_trade_id"] == "t1"

@pytest.mark.asyncio
async def test_place_smart_order(mock_httpx_client):
    client = ExecutionClient()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ord": "ok"}
    mock_httpx_client.post.return_value = mock_response
    
    result = await client.place_smart_order({"o":"d"})
    assert result == {"ord": "ok"}
    args, _ = mock_httpx_client.post.call_args
    assert "/smart-orders" in args[0]

@pytest.mark.asyncio
async def test_get_account_summary(mock_httpx_client):
    client = ExecutionClient()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"balance": 1000}
    mock_httpx_client.post.return_value = mock_response
    
    result = await client.get_account_summary({"key": "val"})
    
    assert result == {"balance": 1000}
    args, kwargs = mock_httpx_client.post.call_args
    assert "account/summary" in args[0]
    assert kwargs["json"]["broker"] == {"key": "val"}

@pytest.mark.asyncio
async def test_get_open_trades(mock_httpx_client):
    client = ExecutionClient()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [{"id": 1}]}
    mock_httpx_client.post.return_value = mock_response
    
    result = await client.get_open_trades({"key": "val"})
    
    assert len(result) == 1
    assert result[0]["id"] == 1

@pytest.mark.asyncio
async def test_place_order_error(mock_httpx_client):
    client = ExecutionClient()
    mock_httpx_client.post.side_effect = Exception("Network Error")
    
    with pytest.raises(Exception, match="Network Error"):
        await client.place_order({}, {})
