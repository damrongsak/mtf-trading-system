import pytest
from unittest.mock import MagicMock, AsyncMock
import sys
import os

# Ensure 'app' is found in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.strategy_advisor import StrategyAdvisorAgent, AgentState
from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.services.memory import MemoryService

@pytest.mark.asyncio
async def test_agent_graph_flow():
    # 1. Mock Dependencies
    mock_gemini = MagicMock(spec=GeminiClient)
    mock_gemini.client = MagicMock()
    mock_gemini.client.aio.models.generate_content = AsyncMock()
    
    # Mock responses for different nodes
    async def gemini_side_effect(model, contents):
        mock_resp = MagicMock()
        if "Query Optimizer" in str(contents):
            mock_resp.text = '{"optimized_query": "Build a Delta Neutral Strategy", "intent": "STRATEGY_DESIGN"}'
        elif "Decompose" in str(contents):
            mock_resp.text = '["Step 1: Get Risk Models", "Step 2: Get Code"]'
        elif "Act as a Hedge Fund Quant" in str(contents):
            mock_resp.text = "Here is the Delta Neutral Plan..."
        elif "Analyze this interaction" in str(contents):
            mock_resp.text = "User prefers Delta Neutral."
        else:
            mock_resp.text = "Generic Response"
        return mock_resp

    mock_gemini.client.aio.models.generate_content.side_effect = gemini_side_effect

    mock_rag = MagicMock(spec=RAGService)
    mock_rag.search_documentation = AsyncMock(return_value=[{"content": "Doc 1"}])
    mock_rag.search_similar_strategies = AsyncMock(return_value=[{"code": "Strategy A"}])

    mock_memory = MagicMock(spec=MemoryService)
    mock_memory.get_user_context = AsyncMock(return_value="User likes low risk.")
    mock_memory.add_user_fact = AsyncMock()

    # 2. Initialize Agent
    agent = StrategyAdvisorAgent(mock_rag, mock_gemini, memory_service=mock_memory)

    # 3. Run Agent
    response = await agent.run("build dn strat", user_id="test_user")

    # 4. Verify Flow
    assert "Delta Neutral Plan" in response
    
    # Verify Optimizer called
    assert mock_gemini.client.aio.models.generate_content.call_count >= 3
    
    # Verify Memory Read
    mock_memory.get_user_context.assert_called_once()
    
    # Verify RAG Read
    mock_rag.search_documentation.assert_called_once()
    
    # Verify Memory Write (Fact Interaction)
    mock_memory.add_user_fact.assert_called()
    
if __name__ == "__main__":
    import asyncio
    asyncio.run(test_agent_graph_flow())
