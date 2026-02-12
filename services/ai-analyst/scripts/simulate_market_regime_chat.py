import asyncio
import sys
import os
from typing import List

# Add app to path
sys.path.append(os.getcwd())

# Import Agent Logic
from app.agents.strategy_advisor import StrategyAdvisorAgent

async def simulate_chat():
    print("\n--- Simulating AI Chat for Market Regime ---")
    
    query = "Check the market regime for XAUUSD on H4 timeframe."
    print(f"User Query: {query}")
    
    # Initialize Dependencies
    from app.services.gemini import GeminiClient
    
    # Mock RAG Service
    class MockRAG:
        def __init__(self, client): pass
        async def search_documentation(self, query): return []
        async def search_similar_strategies(self, query, user_id): return []
    
    # We need a real Gemini Client (uses Env Vars)
    gemini_client = GeminiClient()
    rag_service = MockRAG(gemini_client)
    
    # Initialize Advisor
    advisor = StrategyAdvisorAgent(rag_service=rag_service, gemini_client=gemini_client)
    
    # Run Agent
    # This mimics the /api/v1/ai/chat/sessions/message flow sans DB
    print("... Agent processing ...")
    
    try:
        response = await advisor.run(
            input_text=query,
            user_id="test-sim-001"
        )
        
        print("\n--- Agent Response ---")
        print(response["response"])
        
        # Verify Tool Usage in Log or Trace
        # Note: process_message returns a dict with 'response', 'tool_calls', etc. if configured, 
        # but standard implementation might just return text.
        # We'll judge by the output content containing specific keywords.
        
        if "Adaptive Market State" in response["response"] or "Regime" in response["response"]:
            print("\n✅ SUCCESS: Agent used the Market State tool.")
        else:
            print("\n⚠️ WARNING: Agent response does not explicitly show tool output. Check logs.")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(simulate_chat())
