import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import httpx
from fastapi import HTTPException
from app.services.internal_client import StrategyClient, ExecutionClient

@pytest.fixture
def strategy_client():
    return StrategyClient()

@pytest.fixture
def execution_client():
    return ExecutionClient()

@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_run_backtest_error(strategy_client):
    with patch("httpx.AsyncClient.post", side_effect=httpx.HTTPError("Network Error")):
        with pytest.raises(httpx.HTTPError):
            await strategy_client.run_backtest({})

@pytest.mark.asyncio
async def test_start_strategy_error(strategy_client):
    with patch("httpx.AsyncClient.post", side_effect=httpx.HTTPError("Network Error")):
        with pytest.raises(httpx.HTTPError):
            await strategy_client.start_strategy({}, {})

@pytest.mark.asyncio
async def test_stop_strategy_error(strategy_client):
    with patch("httpx.AsyncClient.post", side_effect=httpx.HTTPError("Network Error")):
        with pytest.raises(httpx.HTTPError):
            await strategy_client.stop_strategy("uuid")

@pytest.mark.asyncio
async def test_get_account_summary_error(execution_client):
    # Code uses POST for account summary
    with patch("httpx.AsyncClient.post", side_effect=httpx.HTTPError("Network Error")):
        with pytest.raises(httpx.HTTPError):
            await execution_client.get_account_summary({"broker_config": "tb"})

@pytest.mark.asyncio
async def test_place_order_error(execution_client):
    # If API returns 400, raise_for_status raises HTTPStatusError
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad Order"
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError("Bad Request", request=None, response=mock_resp)
    
    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(httpx.HTTPStatusError) as exc:
             await execution_client.place_order({}, broker_config={})
        assert exc.value.response.status_code == 400

@pytest.mark.asyncio
async def test_place_order_network_error(execution_client):
    with patch("httpx.AsyncClient.post", side_effect=httpx.HTTPError("Network Error")):
        with pytest.raises(httpx.HTTPError):
             await execution_client.place_order({}, broker_config={})
