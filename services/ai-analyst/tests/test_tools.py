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
            {"timestamp": "2024-01-01T00:00:00Z", "close": 2000.0}
        ]
    }
    mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_resp
    
    result = await tool.arun({"symbol": "XAU/USD", "timeframe": "M15"})
    
    assert "2000.0" in result
    mock_aiohttp_session.get.assert_called_once()
    assert "XAU/USD" in mock_aiohttp_session.get.call_args[1]['params']['symbol']
    assert mock_aiohttp_session.get.call_args[1]['params']['timeframe'] == "M15"

@pytest.mark.asyncio
async def test_market_context_tool_failure(mock_aiohttp_session):
    tool = GetMarketContextTool()
    
    mock_resp = AsyncMock()
    mock_resp.status = 500
    mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_resp
    
    result = await tool.arun({"symbol": "XAU/USD", "timeframe": "M15"})
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
    
    result = await tool.arun({"symbol": "XAU/USD", "code": "code..."})
    
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
    
    result = await tool.arun({"symbol": "XAU/USD", "code": "bad code"})
    assert "Strategy Core Error (400): Syntax Error" in result

@pytest.mark.asyncio
async def test_economic_calendar_tool():
    tool = GetEconomicCalendarTool()
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"datetime": "2024-01-01T10:00:00Z", "country": "USD", "impact": "High", "title": "NFP", "forecast": "200k", "previous": "210k"}
        ]
        mock_get.return_value = mock_resp
        
        # Test USD
        with patch("redis.asyncio.from_url") as mock_redis_cls:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None
            mock_redis_cls.return_value = mock_redis
            
            result_usd = await tool.arun("USD")
            assert "USD: NFP" in result_usd
            assert "High" in result_usd
        
        # Test XYZ (empty response)
        mock_resp.json.return_value = []
        result_xyz = await tool.arun("XYZ")
        assert "No economic events found" in result_xyz

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
    
    result = await tool.arun({}, auth_token="fake_token")
    
    # Verify Parsing
    assert "$10,500.50" in result
    assert "$10,000.00" in result
    assert "Active Positions: 2" in result
    assert "XAU/USD: PnL $50.00" in result
    
    # Mock Failure
    mock_resp.status = 500
    mock_resp.text.return_value = "Server Error"
    result = await tool.arun({}, auth_token="fake_token")
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
    
    result = await tool.arun("XAU/USD")
    assert "BULLISH" in result
    assert "SMC" in result
    
    # Mock Failure
    mock_resp.status = 500
    mock_resp.text.return_value = "Server Error"
    result = await tool.arun("XAU/USD")
    assert "Error fetching signals" in result

@pytest.mark.asyncio
async def test_google_search_tool(mock_aiohttp_session):
    tool = GoogleSearchTool()
    
    with patch("redis.asyncio.from_url") as mock_redis_cls:
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None # Cache miss
        mock_redis_cls.return_value = mock_redis
        
        # Mock API Gateway Success
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = {
            "data": [{"title": "Gold up $50", "source": "Bloomberg", "published_at": "2024-03-10"}]
        }
        mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_resp
        
        result = await tool.arun("XAUUSD")
        assert "Internal News Feed" in result
        assert "Gold up $50" in result
        assert "Bloomberg" in result
