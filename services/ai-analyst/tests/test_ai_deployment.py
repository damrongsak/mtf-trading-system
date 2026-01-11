import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.tools.alpha_deployer import AlphaDeployerTool
from app.tools.strategy_retriever import StrategyRetrieverTool

@pytest.fixture
def mock_aiohttp_session():
    with patch("aiohttp.ClientSession") as mock_session_cls:
        mock_session = MagicMock()
        # Mock Context Manager enter
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        yield mock_session

@pytest.mark.asyncio
async def test_alpha_deployer_tool_success(mock_aiohttp_session):
    tool = AlphaDeployerTool()
    
    # Mock Response
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {"status": "success", "data": {"id": "strat-uuid-123"}}
    
    # Setup session.post to return the mock_resp context
    mock_aiohttp_session.post.return_value.__aenter__.return_value = mock_resp
    
    result = await tool._arun(
        user_id="user-1",
        symbol="EUR/USD",
        formula="rsi(close, 14) < 30"
    )
    
    # Verify
    assert "Successfully deployed" in result
    assert "strat-uuid-123" in result
    
    # Verify Payload
    mock_aiohttp_session.post.assert_called_once()
    payload = mock_aiohttp_session.post.call_args[1]['json']
    assert payload['template_id'] == "ALPHA_ENGINE_V1"
    assert payload['config_json']['formula'] == "rsi(close, 14) < 30"

@pytest.mark.asyncio
async def test_alpha_deployer_tool_failure(mock_aiohttp_session):
    tool = AlphaDeployerTool()
    
    mock_resp = AsyncMock()
    mock_resp.status = 400
    mock_resp.text.return_value = "Invalid Syntax"
    mock_aiohttp_session.post.return_value.__aenter__.return_value = mock_resp
    
    result = await tool._arun(user_id="u1", symbol="X", formula="bad")
    
    assert "Failed to deploy: 400" in result
    assert "Invalid Syntax" in result

@pytest.mark.asyncio
async def test_strategy_retriever_tool_success(mock_aiohttp_session):
    tool = StrategyRetrieverTool()
    
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {
        "data": [
            {
                "id": "s1", 
                "name": "S1", 
                "template_id": "ALPHA_ENGINE_V1", 
                "is_active": True,
                "config_json": {"meta_description": "My first bot"}
            },
            {
                "id": "s2", 
                "name": "S2", 
                "template_id": "SMC_V1", 
                "is_active": False 
            }
        ]
    }
    mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_resp
    
    result = await tool._arun(user_id="user-1")
    
    # Should only return active strategies (s1)
    assert len(result) == 1
    assert result[0]['id'] == "s1"
    assert result[0]['description'] == "My first bot"

@pytest.mark.asyncio
async def test_strategy_retriever_tool_empty(mock_aiohttp_session):
    tool = StrategyRetrieverTool()
    
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {"data": []}
    mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_resp
    
    result = await tool._arun(user_id="user-1")
    assert result == []
