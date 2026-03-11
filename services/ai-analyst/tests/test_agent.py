import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.agents.strategy_advisor import StrategyAdvisorAgent

@pytest.fixture
def mock_agent_deps():
    with patch("app.agents.strategy_advisor.ChatGoogleGenerativeAI") as mock_llm, \
         patch("app.agents.strategy_advisor.settings") as mock_settings, \
         patch("app.agents.strategy_advisor.create_react_agent") as mock_create_agent:
        
        # mock_settings.gemini.api_key = "fake_key"
        
        # Mock graph run
        mock_graph = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Market looks bullish due to X, Y, Z."
        mock_graph.ainvoke = AsyncMock(return_value={"messages": [mock_message]})
        
        mock_create_agent.return_value = mock_graph
        
        yield mock_create_agent

@pytest.mark.asyncio
async def test_strategy_advisor_run(mock_agent_deps):
    # StrategyAdvisorAgent requires more deps in __init__, but for this test we mock the graph
    with patch("app.agents.strategy_advisor.StrategyAdvisorAgent.__init__", return_value=None):
        agent = StrategyAdvisorAgent(None, None)
        agent.graph = mock_agent_deps.return_value
        
        result = await agent.run("Status Report")
        
        assert "Market looks bullish" in result
        
        # Verify graph invoked
        agent.graph.ainvoke.assert_called_once()
