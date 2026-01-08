import pytest
from unittest.mock import MagicMock, AsyncMock, patch, ANY
from app.agents.universal import UniversalAgent
from app.schemas.agent import AgentConfig
from app.core.workflow import registry
from langchain_core.tools import tool

@pytest.mark.asyncio
async def test_universal_agent_initialization():
    # 1. Register a Mock Tool
    @tool
    def mock_calculator(a: int, b: int) -> int:
        """Adds two numbers."""
        return a + b
        
    registry.register("calculator", mock_calculator)
    
    # 2. Create Config
    config = AgentConfig(
        name="Math Bot",
        role="You are a mathematician.",
        tools=["calculator"],
        model="gemini-2.5-flash"
    )
    
    # 3. Initialize Agent
    # Mock LLM to avoid API calls
    with patch.object(UniversalAgent, "__init__", return_value=None) as mock_init:
        # We can't easily test full run without mocking LangGraph/LLM deeply.
        # So we'll test the Logic of init manually if we weren't mocking it completely.
        # Let's actually test the 'real' init but mock ChatGoogleGenerativeAI
        pass

    # Real Init with Mocked LLM
    with patch("app.agents.universal.ChatGoogleGenerativeAI") as MockLLM:
        with patch("app.agents.universal.create_react_agent") as MockGraph:
            agent = UniversalAgent(config)
            
            # Assert Tools Loaded
            assert len(agent.tools) == 1
            assert agent.tools[0].name == "mock_calculator"
            
            # Assert LLM Init
            MockLLM.assert_called_with(
                model="gemini-2.5-flash",
                google_api_key=ANY,
                temperature=0.1
            )
            
            # Assert Graph Creation
            MockGraph.assert_called_once()


@pytest.mark.asyncio
async def test_universal_agent_run():
    # Mock Graph execution
    config = AgentConfig(name="Test", role="Params", tools=[])
    
    with patch("app.agents.universal.ChatGoogleGenerativeAI"), \
         patch("app.agents.universal.create_react_agent") as MockGraph:
        
        mock_compiled_graph = AsyncMock()
        mock_compiled_graph.ainvoke.return_value = {
            "messages": [MagicMock(content="Hello World")]
        }
        MockGraph.return_value = mock_compiled_graph
        
        agent = UniversalAgent(config)
        response = await agent.run("Hi")
        
        assert response == "Hello World"
        mock_compiled_graph.ainvoke.assert_called_once()
