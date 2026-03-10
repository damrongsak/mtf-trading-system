import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.strategy_advisor import StrategyAdvisorAgent, AgentState
from langchain_core.messages import HumanMessage, AIMessage
import uuid
import json

@pytest.fixture
def mock_dependencies():
    mock_rag = AsyncMock()
    mock_gemini = AsyncMock() # GeminiClient mock
    mock_gemini.model_id = "gemini-2.5-flash"
    mock_gemini.client = AsyncMock()
    
    async def side_effect_func(model=None, contents=None, **kwargs):
        prompt = contents[0] if isinstance(contents, list) else str(contents)
        
        # Default responses based on expected JSON schemas in nodes
        if "optimized_query" in prompt:
            return {"text": '{"optimized_query": "test", "intent": "CHAT"}'}
        if "severity" in prompt:
            return {"text": '{"severity": "ROUTINE", "rationale": "ok"}'}
        if "next_node" in prompt or "ROUTE" in prompt:
            return {"text": '{"next_node": "END", "reasoning": "all good"}'}
        if "plan_steps" in prompt:
            return {"text": '{"plan_steps": ["step1"]}'}
        if "is_satisfactory" in prompt:
            return {"text": '{"is_satisfactory": true, "feedback": ""}'}
        
        return {"text": "Default AI response"}

    mock_gemini.generate_content.side_effect = side_effect_func
    return mock_rag, mock_gemini

@pytest.mark.asyncio
async def test_strategy_advisor_iteration_limit(mock_dependencies):
    mock_rag, mock_gemini = mock_dependencies
    
    # Override evaluation to keep iterating
    async def evaluation_side_effect(model=None, contents=None, **kwargs):
        prompt = contents[0] if isinstance(contents, list) else str(contents)
        if "is_satisfactory" in prompt:
            return {"text": '{"is_satisfactory": false, "feedback": "Need more detail"}'}
        if "optimized_query" in prompt:
             return {"text": '{"optimized_query": "test", "intent": "CHAT"}'}
        if "severity" in prompt:
             return {"text": '{"severity": "ROUTINE", "rationale": "ok"}'}
        return {"text": "Developing..."}

    mock_gemini.generate_content.side_effect = evaluation_side_effect
    
    advisor = StrategyAdvisorAgent(mock_rag, mock_gemini)
    
    state: AgentState = {
        "input_text": "Optimize strategy",
        "messages": [HumanMessage(content="Optimize strategy")],
        "user_id": str(uuid.uuid4()),
        "user_config": {},
        "context": {},
        "scratchpad": [],
        "iteration_count": 4, # Start near limit
        "tool_loop_count": 0,
        "evaluation_feedback": "",
        "is_satisfactory": False
    }
    
    new_state = await advisor.graph.ainvoke(state)
    assert new_state["iteration_count"] >= 5

@pytest.mark.asyncio
async def test_strategy_advisor_rejection_logic(mock_dependencies):
    mock_rag, mock_gemini = mock_dependencies
    
    # Specific sequence for rejection test
    responses = [
        {"text": '{"optimized_query": "Risky strat", "intent": "STRATEGY_DESIGN"}'}, # optimizer
        {"text": '{"severity": "VOLATILITY", "rationale": "risk"}'}, # classifier
        {"text": '{"next_node": "decompose", "reasoning": "risk"}'}, # router -> decompose
        {"text": '{"plan_steps": ["analyze risk"]}'}, # decompose
        {"text": "Reasoning summary"}, # reason
        {"text": "Risky Code"}, # generate
        {"text": '{"is_satisfactory": false, "feedback": "REJECT: Too dangerous"}'}, # evaluator (FAIL)
        {"text": "Fixed Code"} # generate again
    ]
    
    call_count = 0
    async def custom_side_effect(*args, **kwargs):
        nonlocal call_count
        if call_count < len(responses):
            res = responses[call_count]
            call_count += 1
            return res
        return {"text": "END"}

    mock_gemini.generate_content.side_effect = custom_side_effect
    
    advisor = StrategyAdvisorAgent(mock_rag, mock_gemini)
    
    state: AgentState = {
        "input_text": "High risk strategy",
        "messages": [HumanMessage(content="High risk strategy")],
        "user_id": "test",
        "user_config": {},
        "context": {},
        "scratchpad": [],
        "iteration_count": 0,
        "tool_loop_count": 0,
        "evaluation_feedback": "",
        "is_satisfactory": False
    }
    
    new_state = await advisor.graph.ainvoke(state)
    assert new_state["iteration_count"] > 0
    assert "REJECT" in new_state["evaluation_feedback"]
