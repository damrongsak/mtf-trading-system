import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.agents.market_observer import MarketObserverAgent

@pytest.fixture
def mock_agent_deps():
    with patch("app.agents.market_observer.ChatGoogleGenerativeAI") as mock_llm, \
         patch("app.agents.market_observer.settings") as mock_settings, \
         patch("app.agents.market_observer.create_react_agent") as mock_create_agent:
        
        mock_settings.gemini.api_key = "fake_key"
        
        # Mock graph run
        mock_graph = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Market looks bullish due to X, Y, Z."
        mock_graph.ainvoke = AsyncMock(return_value={"messages": [mock_message]})
        
        mock_create_agent.return_value = mock_graph
        
        yield mock_create_agent

@pytest.mark.asyncio
async def test_market_observer_run(mock_agent_deps):
    agent = MarketObserverAgent()
    
    result = await agent.run("Status Report")
    
    assert "Market looks bullish" in result
    
    # Verify graph invoked
    mock_agent_deps.return_value.ainvoke.assert_called_once()
