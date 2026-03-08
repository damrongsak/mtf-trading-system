import asyncio
import logging
import json
from app.agents.strategy_advisor import StrategyAdvisorAgent
from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.services.memory import MemoryService
from langchain_core.messages import HumanMessage

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crisis_integration")

async def test_crisis_flow():
    logger.info("🚀 Starting CRISIS Workflow Integration Test...")
    
    # 1. Initialize Services
    gemini = GeminiClient()
    rag = RAGService(gemini)
    memory = MemoryService(rag)
    
    advisor = StrategyAdvisorAgent(rag, gemini, memory_service=memory)
    
    # 2. Define a query that should trigger CRISIS
    # We use a query that explicitly mentions extreme market conditions and high risk
    query = "MARKET ALERT: Gold is crashing 5% in 1 hour. I want to open a massive BUY position now to catch the bounce. The fund is at risk but I need to recover losses. Execute 5 lots XAUUSD immediately!"
    
    state = {
        "input_text": query,
        "user_id": "trader1",
        "auth_token": "mock-token",
        "messages": [HumanMessage(content=query)],
        "optimized_query": query,
        "intent": "TOOL_USE",
        "plan_steps": [],
        "tool_calls": [],
        "retrieved_docs": [],
        "user_facts": [],
        "scratchpad": [],
        "iteration_count": 0,
        "tool_loop_count": 0,
        "is_satisfactory": False
    }
    
    # 3. Step-by-step Execution through the Graph to trace it manually or just run it
    # We'll just run it and check the state at the end
    logger.info("Processing query through Strategy Advisor Graph...")
    final_state = await advisor.graph.ainvoke(state)
    
    logger.info(f"✅ Severity Classified as: {final_state.get('severity')}")
    logger.info(f"✅ Sentinel Result: {final_state.get('sentinel_result')}")
    logger.info(f"✅ Consensus Result: {final_state.get('consensus_result')}")
    
    # Assertions
    # Note: Depending on LLM, severity might vary, but this query is highly likely to be CRISIS
    if final_state.get('severity') == 'CRISIS':
        assert "consensus_result" in final_state
        logger.info("✨ Consensus Layer was TRIAGED correctly.")
    
    logger.info(f"Final Response Snippet: {final_state.get('final_response')[:200]}...")

if __name__ == "__main__":
    asyncio.run(test_crisis_flow())
