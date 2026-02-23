import asyncio
import os
import sys

# Add the current directory to sys.path to allow importing app
sys.path.append(os.getcwd())

from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.agents.strategy_advisor import StrategyAdvisorAgent
from app.core.config import settings

async def main():
    print("--- Verifying StrategyAdvisorAgent Fix ---")
    
    # Initialize services
    gemini = GeminiClient()
    rag = RAGService(gemini)
    agent = StrategyAdvisorAgent(rag_service=rag, gemini_client=gemini)
    
    query = "give me trading entry for asia session in 5min timeframe in short message"
    user_id = "test-user"
    auth_token = os.getenv("INTERNAL_API_KEY", "dev-internal-key")
    
    print(f"Query: {query}")
    print("Running agent...")
    
    try:
        result = await agent.run(
            input_text=query,
            user_id=user_id,
            auth_token=auth_token,
            thread_id="test-thread-asia-entry"
        )
        
        print("\n--- Agent Response ---")
        print(result.get("response"))
        print("\n--- Agent Thoughts ---")
        print(result.get("thoughts")[:500] + "..." if result.get("thoughts") else "No thoughts.")
        
        response_text = result.get("response", "")
        if response_text and "no text" not in response_text.lower() and "safety filters" not in response_text.lower():
            print("\n✅ Success: Agent returned a substantial response.")
        else:
            print("\n❌ Failure: Agent returned empty or error response.")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
