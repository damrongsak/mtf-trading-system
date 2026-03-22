import asyncio
import os
import json
import sys
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.append("/home/dan/workspace/mtf-trading-system/services/ai-analyst")

from app.agents.strategy_advisor import StrategyAdvisorAgent
from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.core.config import settings

async def verify():
    print("🚀 Starting Phase 67 World-Class Data Retrieval Verification...")
    
    # Initialize real services (using env vars from container context)
    gemini = GeminiClient()
    rag = RAGService()
    
    agent = StrategyAdvisorAgent(rag_service=rag, gemini_client=gemini)
    
    user_id = "00000000-0000-0000-0000-000000000001"
    query = "Check EUR COT net positions for March 8 to March 22, 2026. Do we have this in the local database? If not, find it."
    
    print(f"User Query: {query}")
    print("--- Thinking Process Start ---")
    
    # Using run to get full state for debugging/verification
    result = await agent.run(
        input_text=query,
        user_id=user_id,
        auth_token="mock_token"
    )
    
    print("\n--- Final Response ---")
    print(result.get("response"))
    
    print("\n--- Metadata Audit ---")
    metadata = result.get("metadata", {})
    print(f"Intent detected: {result.get('intent')}")
    print(f"Fact Check Result: {metadata.get('fact_check_result', 'N/A')}")
    print(f"Data Gap Detected: {metadata.get('data_gap_detected', 'N/A')}")
    
    # Check for the Transparency Protocol phrase
    response = result.get("response", "")
    if "Local database currently lacks" in response or "Local database contains no" in response:
        print("✅ SUCCESS: Transparency Protocol Triggered.")
    else:
        print("❌ FAILURE: Transparency Protocol NOT Triggered.")
        
    if "AUTONOMOUS DATA RECOVERY" in str(result.get("thoughts", "")) or "node_data_recovery" in str(result.get("thoughts", "")):
        print("✅ SUCCESS: Data Recovery Node engaged.")
    else:
        # Check thoughts if available
        print(f"Thoughts trace: {result.get('thoughts')[:200]}...")

if __name__ == "__main__":
    asyncio.run(verify())
