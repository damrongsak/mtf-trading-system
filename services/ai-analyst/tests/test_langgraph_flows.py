import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.universal import UniversalAgent
from app.agents.supervisor import SupervisorAgent
from app.schemas.agent import AgentConfig
from langchain_core.messages import HumanMessage, AIMessage

@pytest.fixture
def mock_dependencies():
    mock_rag = AsyncMock()
    mock_gemini = AsyncMock()
    mock_gemini.model_id = "gemini-2.5-flash"
    mock_gemini.client = AsyncMock()
    return mock_rag, mock_gemini

@pytest.mark.asyncio
async def test_universal_agent_flow(mock_dependencies):
    mock_rag, mock_gemini = mock_dependencies
    
    config = AgentConfig(
        name="Test Agent",
        role="You are a test agent",
        tools=["market_state"]
    )
    
    # Mock ChatGoogleGenerativeAI to avoid real API calls
    with patch("app.agents.universal.ChatGoogleGenerativeAI") as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        
        agent = UniversalAgent(config)
        
        # Mock the graph ainvoke directly
        agent.graph = AsyncMock()
        agent.graph.ainvoke = AsyncMock(return_value={
            "messages": [AIMessage(content="Market looks bullish.")]
        })
        
        # Test run method
        result = await agent.run("How is the gold market?")
        assert "Market looks bullish" in result

@pytest.mark.asyncio
async def test_supervisor_agent_routing(mock_dependencies):
    mock_rag, mock_gemini = mock_dependencies
    supervisor = SupervisorAgent(mock_gemini)
    
    # Mock gemini client response for routing
    mock_response = MagicMock()
    # supervisor.py line 49 expects response.text
    mock_response.text = '{"next_node": "StrategyAdvisor", "reasoning": "User is asking about code"}'
    
    # supervisor.py line 44: await client.aio.models.generate_content
    mock_gemini.client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    
    state = {
        "messages": [HumanMessage(content="Design me a strategy")],
        "next_node": None,
        "scratchpad": [],
        "user_config": {}
    }
    
    new_state = await supervisor.route(state)
    assert new_state["next_node"] == "StrategyAdvisor"
    assert "StrategyAdvisor" in new_state["scratchpad"][0]
