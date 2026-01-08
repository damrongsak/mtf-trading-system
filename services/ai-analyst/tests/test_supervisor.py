import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.supervisor import SupervisorAgent
from app.core.workflow import AgentState
from langchain_core.messages import HumanMessage

@pytest.mark.asyncio
async def test_supervisor_routing_strategy():
    # Mock Gemini
    mock_gemini = MagicMock()
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.text = '{"next_node": "StrategyAdvisor", "reasoning": "User asked for code"}'
    
    mock_client.aio.models.generate_content.return_value = mock_response
    mock_gemini.client = mock_client
    mock_gemini.model_id = "dummy-model"

    supervisor = SupervisorAgent(mock_gemini)
    
    state: AgentState = {
        "messages": [HumanMessage(content="Write a strategy")],
        "scratchpad": [],
        "user_config": {},
        "context": {},
        "user_id": "test"
    }
    
    new_state = await supervisor.route(state)
    
    assert new_state["next_node"] == "StrategyAdvisor"

@pytest.mark.asyncio
async def test_supervisor_byok_usage():
    # Verify BYOK key is used via client_factory
    
    mock_default_client = AsyncMock()
    mock_custom_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.text = '{"next_node": "General", "reasoning": "Hi"}'
    mock_custom_client.aio.models.generate_content.return_value = mock_response
    
    # Mock Gemini Service having a client_factory
    mock_gemini = MagicMock()
    mock_gemini.client = mock_default_client
    mock_gemini.model_id = "default"
    mock_gemini.client_factory = MagicMock(return_value=mock_custom_client)
    
    supervisor = SupervisorAgent(mock_gemini)
    
    state: AgentState = {
        "messages": [HumanMessage(content="Hello")],
        "scratchpad": [],
        "user_config": {"api_key": "custom-key", "model_id": "custom-model"},
        "context": {},
        "user_id": "test"
    }
    
    await supervisor.route(state)
    
    # Verify factory called
    mock_gemini.client_factory.assert_called_with(api_key="custom-key")
    
    # Verify custom client used
    mock_custom_client.aio.models.generate_content.assert_called()
    args = mock_custom_client.aio.models.generate_content.call_args
    assert args.kwargs['model'] == "custom-model"
