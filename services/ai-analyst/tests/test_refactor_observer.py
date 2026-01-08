import pytest
from app.core.bootstrap import bootstrap_tools
from app.agents.universal import UniversalAgent
from app.schemas.agent import AgentConfig
from unittest.mock import patch, ANY

@pytest.mark.asyncio
async def test_market_observer_refactor_config():
    # 1. Bootstrap Tools (populate registry)
    bootstrap_tools()
    
    # 2. Define Market Observer Config
    config = AgentConfig(
        name="Market Observer",
        role="You are an expert financial analyst.",
        tools=[
            "get_market_context",
            "get_technical_signals",
            "get_account_status",
            "get_economic_calendar",
            "google_search"
        ],
        model="gemini-2.5-flash"
    )
    
    # 3. Initialize Universal Agent
    # Mock LLM/Graph creation as it requires API keys
    with patch("app.agents.universal.ChatGoogleGenerativeAI"), \
         patch("app.agents.universal.create_react_agent"):
        
        agent = UniversalAgent(config)
        
        # 4. Verify Tools are loaded correctly
        tool_names = [t.name for t in agent.tools]
        assert "get_market_context" in tool_names
        assert "get_technical_signals" in tool_names
        assert len(agent.tools) == 5
