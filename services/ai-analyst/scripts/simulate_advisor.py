
import asyncio
import logging
import json
import sys
import os

# Setup paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.agents.strategy_advisor import StrategyAdvisorAgent
from app.core.bootstrap import bootstrap_tools
from app.core.globals import services

# Configuration
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("simulation")

async def simulate():
    # 1. Setup Services
    bootstrap_tools()
    gemini = GeminiClient()
    # Mock RAG if needed, but here we want actual logic
    rag = RAGService(gemini)
    
    agent = StrategyAdvisorAgent(
        rag_service=rag,
        gemini_client=gemini,
        checkpointer=None, # In-memory not needed for one-shot
        memory_service=None
    )
    
    prompt = "Fetching SMC Analysis for XAUUSD W1"
    user_id = "tester-123"
    
    print(f"\n> User: {prompt}")
    
    try:
        result = await agent.run(
            input_text=prompt,
            user_id=user_id,
            auth_token=None # Tool uses direct DB access usually
        )
        
        print("\n" + "="*50)
        print("🤖 AI RESPONSE:")
        print(result.get("response"))
        print("\n" + "="*50)
        print("🧠 THOUGHTS (If any):")
        print(result.get("thoughts"))
        print("="*50)
        
    except Exception as e:
        print(f"Agent failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(simulate())
