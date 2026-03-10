import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.strategy_advisor import StrategyAdvisorAgent, AgentState
from langchain_core.messages import HumanMessage

@pytest.mark.asyncio
async def test_strategy_advisor_run():
    # Setup Mocks
    mock_rag = AsyncMock()
    mock_rag.search_documentation.return_value = [{"filename": "spec.md", "content": "API Spec"}]
    mock_rag.search_similar_strategies.return_value = [{"code": "def old_strat(): pass"}]

    mock_gemini = MagicMock()
    mock_gemini.model_id = "test-model"
    mock_client = AsyncMock()
    # Mock responses for Plan and Generate steps
    mock_plan_resp = MagicMock()
    mock_plan_resp.text = "Step 1: Write code"
    mock_code_resp = MagicMock()
    mock_code_resp.text = "def strategy(): pass"
    
    mock_client.aio.models.generate_content.side_effect = [mock_plan_resp, mock_code_resp]
    mock_gemini.client = mock_client

    advisor = StrategyAdvisorAgent(mock_rag, mock_gemini)
    
    state: AgentState = {
        "input_text": "Create a strategy",
        "messages": [HumanMessage(content="Create a strategy")],
        "user_id": "test",
        "user_config": {},
        "context": {},
        "scratchpad": [],
        "iteration_count": 0,
        "tool_loop_count": 0,
        "evaluation_feedback": "",
        "is_satisfactory": False
    }
    
    # Run
    new_state = await advisor.graph.ainvoke(state)
    
    # Verify Flow
    mock_rag.search_documentation.assert_called_once()
    assert "Plan: Step 1: Write code" in new_state["scratchpad"][0]
    assert new_state["final_response"] == "def strategy(): pass"

@pytest.mark.asyncio
async def test_strategy_advisor_multimodal_file():
    # Setup Mocks
    mock_rag = AsyncMock()
    mock_rag.search_documentation.return_value = []
    mock_rag.search_similar_strategies.return_value = []

    mock_gemini = MagicMock()
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.text = "Plan"
    mock_client.aio.models.generate_content.return_value = mock_resp
    mock_gemini.client = mock_client

    advisor = StrategyAdvisorAgent(mock_rag, mock_gemini)
    
    state: AgentState = {
        "input_text": "Analyze this chart",
        "messages": [HumanMessage(content="Analyze this chart")],
        "user_id": "test",
        "user_config": {},
        "context": {
            "file_context": {"type": "base64", "data": "ABCD", "mime_type": "image/png"}
        },
        "scratchpad": [],
        "iteration_count": 0,
        "tool_loop_count": 0,
        "evaluation_feedback": "",
        "is_satisfactory": False
    }
    
    await advisor.graph.ainvoke(state)
    
    # Verify image data passed to prompt
    call_args = mock_client.aio.models.generate_content.call_args_list[0]
    contents = call_args.kwargs['contents']
    # Contents should be [Text, ImageDict]
    assert len(contents) == 2
    assert contents[1]["mime_type"] == "image/png"
