import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.routers.broker_account import verify_binance_credentials, fetch_binance_instruments, categorize_binance_instrument
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_categorize_binance_instrument():
    assert categorize_binance_instrument({}) == "Crypto"
    assert categorize_binance_instrument({'symbol': 'BTCUSDT'}) == "Crypto"

@pytest.mark.asyncio
@patch("app.routers.broker_account.httpx.AsyncClient")
async def test_verify_binance_credentials_success(mock_client_cls):
    mock_client = AsyncMock()
    mock_client.get.return_value = MagicMock(status_code=200)
    mock_client_cls.return_value.__aenter__.return_value = mock_client
    
    await verify_binance_credentials("api", "secret", False)
    mock_client.get.assert_called_once()

@pytest.mark.asyncio
@patch("app.routers.broker_account.httpx.AsyncClient")
async def test_verify_binance_credentials_failure(mock_client_cls):
    mock_client = AsyncMock()
    mock_client.get.return_value = MagicMock(status_code=401, json=lambda: {"msg": "Invalid"})
    mock_client_cls.return_value.__aenter__.return_value = mock_client
    
    with pytest.raises(ValueError, match="Binance Unauthorized"):
        await verify_binance_credentials("api", "secret", False)

@pytest.mark.asyncio
@patch("app.routers.broker_account.httpx.AsyncClient")
async def test_fetch_binance_instruments_success(mock_client_cls):
    mock_client = AsyncMock()
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {
        "symbols": [
            {"symbol": "BTCUSDT", "status": "TRADING", "baseAsset": "BTC", "quoteAsset": "USDT"},
            {"symbol": "ETHUSDT", "status": "BREAK", "baseAsset": "ETH", "quoteAsset": "USDT"}
        ]
    }
    mock_client.get.return_value = mock_response
    mock_client_cls.return_value.__aenter__.return_value = mock_client
    
    symbols = await fetch_binance_instruments("api", "secret", False)
    assert len(symbols) == 2
    assert symbols[0]['symbol'] == "BTCUSDT"
