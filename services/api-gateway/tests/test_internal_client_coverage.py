import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import httpx
from app.services.internal_client import StrategyClient, ExecutionClient

@pytest.fixture
def strategy_client():
    return StrategyClient()

@pytest.fixture
def execution_client():
    return ExecutionClient()

@pytest.mark.asyncio
async def test_run_backtest_success(strategy_client):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        
        # Explicitly make post an AsyncMock
        mock_instance.post = AsyncMock()
        mock_instance.post.return_value.status_code = 200
        # Ensure json() returns a dict, NOT a coroutine
        mock_instance.post.return_value.json = MagicMock(return_value={"status": "ok"})
        
        res = await strategy_client.run_backtest({"test": 1})
        assert res["status"] == "ok"

@pytest.mark.asyncio
async def test_run_backtest_error(strategy_client):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        
        mock_instance.post = AsyncMock()
        mock_instance.post.side_effect = httpx.RequestError("fail")
        
        with pytest.raises(httpx.RequestError):
            await strategy_client.run_backtest({})

@pytest.mark.asyncio
async def test_run_custom_backtest_success(strategy_client):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        mock_instance.post = AsyncMock()
        mock_instance.post.return_value.json = MagicMock(return_value={"custom": True})
        res = await strategy_client.run_custom_backtest({})
        assert res["custom"] is True

@pytest.mark.asyncio
async def test_run_custom_backtest_fail(strategy_client):
    with patch("httpx.AsyncClient") as mock_client_cls:
         mock_instance = mock_client_cls.return_value.__aenter__.return_value
         mock_instance.post = AsyncMock()
         mock_instance.post.side_effect = Exception("error")
         with pytest.raises(Exception):
             await strategy_client.run_custom_backtest({})

@pytest.mark.asyncio
async def test_run_optimization_success(strategy_client):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        mock_instance.post = AsyncMock()
        mock_instance.post.return_value.json = MagicMock(return_value={"opt": True})
        res = await strategy_client.run_optimization({})
        assert res["opt"] is True

@pytest.mark.asyncio
async def test_run_monte_carlo_success(strategy_client):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        mock_instance.post = AsyncMock()
        mock_instance.post.return_value.json = MagicMock(return_value={"mc": True})
        res = await strategy_client.run_monte_carlo({})
        assert res["mc"] is True

@pytest.mark.asyncio
async def test_start_strategy_success(strategy_client):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        mock_instance.post = AsyncMock()
        mock_instance.post.return_value.json = MagicMock(return_value={"started": True})
        res = await strategy_client.start_strategy("123", {})
        assert res["started"] is True

@pytest.mark.asyncio
async def test_stop_strategy_success(strategy_client):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        mock_instance.post = AsyncMock()
        mock_instance.post.return_value.json = MagicMock(return_value={"stopped": True})
        res = await strategy_client.stop_strategy("123")
        assert res["stopped"] is True

# Execution Client Tests
@pytest.mark.asyncio
async def test_get_account_summary_success(execution_client):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        mock_instance.post = AsyncMock()
        mock_instance.post.return_value.json = MagicMock(return_value={"balance": 100})
        res = await execution_client.get_account_summary({})
        assert res["balance"] == 100

@pytest.mark.asyncio
async def test_place_order_success(execution_client):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        mock_instance.post = AsyncMock()
        mock_instance.post.return_value.json = MagicMock(return_value={"id": "ord1"})
        res = await execution_client.place_order({}, {})
        assert res["id"] == "ord1"

@pytest.mark.asyncio
async def test_get_open_trades_success(execution_client):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        mock_instance.post = AsyncMock()
        mock_instance.post.return_value.json = MagicMock(return_value={"data": [{"id": 1}]})
        res = await execution_client.get_open_trades({})
        assert res[0]["id"] == 1

@pytest.mark.asyncio
async def test_close_trade_success(execution_client):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        mock_instance.post = AsyncMock()
        mock_instance.post.return_value.json = MagicMock(return_value={"data": {"closed": True}})
        res = await execution_client.close_trade("t1", {})
        assert res["closed"] is True

@pytest.mark.asyncio
async def test_place_smart_order_success(execution_client):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__aenter__.return_value
        mock_instance.post = AsyncMock()
        mock_instance.post.return_value.json = MagicMock(return_value={"smart": True})
        res = await execution_client.place_smart_order({})
        assert res["smart"] is True
