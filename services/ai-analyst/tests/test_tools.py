import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.tools.market import GetMarketContextTool
from app.tools.strategy import StrategyBacktestTool
from app.tools.calendar import GetEconomicCalendarTool

@pytest.fixture
def mock_aiohttp_session():
    with patch("aiohttp.ClientSession") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        yield mock_session

@pytest.mark.asyncio
async def test_market_context_tool_success(mock_aiohttp_session):
    tool = GetMarketContextTool()
    
    # Mock response
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {
        "data": [
            {"time": "2024-01-01", "close": 2000.0}
        ]
    }
    mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_resp
    
    result = await tool._arun("XAU/USD")
    
    assert "2000.0" in result
    mock_aiohttp_session.get.assert_called_once()
    assert "XAU/USD" in mock_aiohttp_session.get.call_args[1]['params']['symbol']

@pytest.mark.asyncio
async def test_market_context_tool_failure(mock_aiohttp_session):
    tool = GetMarketContextTool()
    
    mock_resp = AsyncMock()
    mock_resp.status = 500
    mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_resp
    
    result = await tool._arun("XAU/USD")
    assert "Error fetching market data: 500" in result

@pytest.mark.asyncio
async def test_strategy_backtest_tool_success(mock_aiohttp_session):
    tool = StrategyBacktestTool()
    
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {
        "status": "COMPLETED",
        "metrics": {
            "total_return_percent": 10.5,
            "sharpe_ratio": 1.5
        }
    }
    mock_aiohttp_session.post.return_value.__aenter__.return_value = mock_resp
    
    result = await tool._arun("XAU/USD", "code...")
    
    assert "Total Return: 10.50%" in result
    assert "Sharpe Ratio: 1.50" in result
    
    # Verify dynamic dates logic (simple check that keys exist)
    call_args = mock_aiohttp_session.post.call_args[1]['json']
    assert 'start_date' in call_args
    assert 'end_date' in call_args

@pytest.mark.asyncio
async def test_strategy_backtest_tool_failure(mock_aiohttp_session):
    tool = StrategyBacktestTool()
    
    mock_resp = AsyncMock()
    mock_resp.status = 400
    mock_resp.text.return_value = "Syntax Error"
    mock_aiohttp_session.post.return_value.__aenter__.return_value = mock_resp
    
    result = await tool._arun("XAU/USD", "bad code")
    assert "Strategy Core Error (400): Syntax Error" in result

@pytest.mark.asyncio
async def test_economic_calendar_tool():
    # This tool currently uses mock data, so we test the logic directly
    tool = GetEconomicCalendarTool()
    
    # Test USD (should find mock events)
    result_usd = await tool._arun("USD")
    assert "HIGH IMPACT Economic Events for USD" in result_usd
    
    # Test XYZ (should find nothing)
    result_xyz = await tool._arun("XYZ")
    assert "No high-impact economic events found for XYZ" in result_xyz

from app.tools.account import GetAccountStatusTool
from app.tools.signal import GetTechnicalSignalsTool
from app.tools.search import GoogleSearchTool

@pytest.mark.asyncio
async def test_account_status_tool(mock_aiohttp_session):
    tool = GetAccountStatusTool()
    
    # Mock Success with Complex Data (API Gateway format)
    # Note: account.py expects 'open_positions' (snake_case)
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {
        "status": "success",
        "data": {
            "balance": "10000.00 USDT",
            "equity": "10500.50",
            "marginAvailable": "10000.50", 
            "open_positions": [
                {"symbol": "XAU/USD", "pnl": 50.0, "risk_usd": 10.0},
                {"symbol": "EUR/USD", "pnl": -20.0, "risk_usd": 10.0}
            ]
        }
    }
    mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_resp
    
    result = await tool._arun()
    
    # Verify Parsing
    # Look for formatted currency strings as output by the tool
    assert "$10,500.50" in result  # Equity (Float parsed & formatted)
    assert "$10,000.00" in result  # Balance
    assert "Active Positions: 2" in result # Should be 2 now with correct key
    assert "XAU/USD: PnL $50.00" in result
    
    # Mock Failure
    mock_resp.status = 500
    mock_resp.text.return_value = "Server Error"
    result = await tool._arun()
    assert "Error fetching account data" in result

@pytest.mark.asyncio
async def test_technical_signals_tool(mock_aiohttp_session):
    tool = GetTechnicalSignalsTool()
    
    # Mock Success
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {
        "data": {"symbol": "XAU/USD", "direction": "BULLISH", "reason": "SMC", "entry_price": 2000}
    }
    mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_resp
    
    result = await tool._arun("XAU/USD")
    assert "BULLISH" in result
    assert "SMC" in result
    
    # Mock Failure
    mock_resp.status = 500
    mock_resp.text.return_value = "Server Error"
    result = await tool._arun("XAU/USD")
    assert "Error fetching signals" in result

@pytest.mark.asyncio
async def test_google_search_tool():
    tool = GoogleSearchTool()
    
    # Needs settings patch for API keys
    with patch("app.tools.search.settings") as mock_settings:
        mock_settings.GOOGLE_SEARCH_API_KEY = "fake"
        mock_settings.GOOGLE_CSE_ID = "fake"
        
        with patch("app.tools.search.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            
            # Mock Success
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json.return_value = {
                "items": [
                    {"title": "Result 1", "snippet": "Snippet 1", "link": "http://example.com"}
                ]
            }
            mock_session.get.return_value.__aenter__.return_value = mock_resp
            
            result = await tool._arun("query")
            assert "Result 1" in result
            assert "Snippet 1" in result
            
            # Mock No Keys
            mock_settings.GOOGLE_SEARCH_API_KEY = None
            result = await tool._arun("query")
            assert "MOCK SEARCH RESULT" in result
