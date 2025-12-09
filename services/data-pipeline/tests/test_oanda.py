import pytest
from unittest.mock import MagicMock, patch
from app.adapters.oanda import OandaClient
from app.core.config import settings
import requests
import json
import re

# Mock settings for testing
@pytest.fixture(autouse=True)
def mock_settings():
    with patch('app.core.config.settings') as mock_settings:
        mock_settings.OANDA_API_KEY = "mock_key"
        mock_settings.OANDA_ACCOUNT_ID = "mock_account"
        mock_settings.OANDA_ENV = "practice"
        yield mock_settings

@patch('requests.Session.request')
def test_fetch_candles_success(mock_request, mock_settings):
    """
    Test that fetch_candles successfully retrieves and processes data.
    """
    # Arrange
    symbol = "XAU_USD"
    timeframe = "M15"
    count = 2

    mock_response_data = {
        'candles': [
            {'time': '2025-01-01T00:00:00.000000000Z', 'volume': 100, 'complete': True,
             'mid': {'o': '1.0', 'h': '1.1', 'l': '0.9', 'c': '1.05'}},
            {'time': '2025-01-01T00:15:00.000000000Z', 'volume': 120, 'complete': True,
             'mid': {'o': '1.05', 'h': '1.15', 'l': '1.0', 'c': '1.10'}}
        ]
    }
    
    # Configure the mock HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    # Ensure .content is a MagicMock and its .decode() returns the correct string
    mock_response.content = MagicMock()
    mock_response.content.decode.return_value = json.dumps(mock_response_data)
    mock_request.return_value = mock_response

    client = OandaClient()

    # Act
    candles = client.fetch_candles(symbol, timeframe, count)

    # Check that requests.Session.request was called correctly
    expected_url = f"https://api-fxtrade.oanda.com/v3/instruments/{symbol}/candles"
    expected_params = {"count": count, "granularity": timeframe, "price": "M"}
    mock_request.assert_called_once_with(
        "GET",
        expected_url,
        params=expected_params,
        headers={},
        stream=False,
        allow_redirects=True
    )
    
    assert len(candles) == 2
    assert candles[0]['time'] == '2025-01-01T00:00:00.000000000Z'
    assert candles[1]['mid']['c'] == '1.10'

@patch('requests.Session.request')
def test_fetch_candles_api_error(mock_request, mock_settings):
    """
    Test that fetch_candles raises an exception on API error.
    """
    # Arrange
    symbol = "XAU_USD"
    timeframe = "H1"
    count = 10

    # Simulate an error response from the API
    error_response_data = {"errorMessage": "Invalid instrument"}
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = error_response_data
    # Ensure .content is a MagicMock and its .decode() returns the correct string
    mock_response.content = MagicMock()
    mock_response.content.decode.return_value = json.dumps(error_response_data)
    mock_request.return_value = mock_response

    client = OandaClient()

    # Act & Assert
    # The oandapyV20.exceptions.V20Error includes the status code and decoded content
    expected_error_regex = re.escape(json.dumps(error_response_data))
    with pytest.raises(Exception, match=expected_error_regex):
        client.fetch_candles(symbol, timeframe, count)

    # Check that requests.Session.request was called correctly
    expected_url = f"https://api-fxtrade.oanda.com/v3/instruments/{symbol}/candles"
    expected_params = {"count": count, "granularity": timeframe, "price": "M"}
    mock_request.assert_called_once_with(
        "GET",
        expected_url,
        params=expected_params,
        headers={},
        stream=False,
        allow_redirects=True
    )