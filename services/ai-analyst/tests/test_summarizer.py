import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.summarizer import SummarizerAgent
from app.core.workflow import AgentState
from langchain_core.messages import HumanMessage, AIMessage

@pytest.mark.asyncio
async def test_summarizer_logic():
    # Setup Logic
    mock_gemini = MagicMock()
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.text = "Discussed various moving average strategies."
    
    # Mocking generate_content to return a dummy summary
    mock_client.aio.models.generate_content.return_value = mock_response
    mock_gemini.client = mock_client
    mock_gemini.model_id = "dummy-model"

    summarizer = SummarizerAgent(mock_gemini)
    
    # Create State with many messages
    messages = [
        HumanMessage(content=f"Message {i}") for i in range(10)
    ]
    
    state: AgentState = {
        "messages": messages,
        "scratchpad": [],
        "user_config": {},
        "context": {},
        "user_id": "test",
        "summary": "Initial summary."
    }
    
    # Run Agent
    new_state = await summarizer.run(state)
    
    # Verify State Update
    assert new_state["summary"] == "Discussed various moving average strategies."
    assert len(new_state["messages"]) == 5 # Should keep last 5
    assert new_state["messages"][0].content == "Message 5"
    assert new_state["messages"][-1].content == "Message 9"
    assert "Context summarized" in new_state["scratchpad"][-1]

@pytest.mark.asyncio
async def test_summarizer_noop():
    # Verify it extracts nothing if few messages
    mock_gemini = MagicMock()
    summarizer = SummarizerAgent(mock_gemini)
    
    messages = [HumanMessage(content="Hi")]
    state = {"messages": messages, "summary": ""}
    
    new_state = await summarizer.run(state)
    
    assert new_state == state # Unchanged
