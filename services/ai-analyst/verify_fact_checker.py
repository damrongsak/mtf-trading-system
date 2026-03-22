import asyncio
import os
import json
import sys

# Add project root
sys.path.append("/home/dan/workspace/mtf-trading-system/services/ai-analyst")

from app.agents.strategy_advisor import StrategyAdvisorAgent
from app.services.gemini import GeminiClient
from app.services.rag import RAGService

async def verify():
    print("🔬 Phase 67 Fact-Checker Logic Verification...")
    
    gemini = GeminiClient()
    rag = RAGService()
    agent = StrategyAdvisorAgent(rag_service=rag, gemini_client=gemini)
    
    # Mock State: Hallucinated response vs Raw Tool Data
    mock_state = {
        "optimized_query": "Check Gold price and COT for March 2026",
        "final_response": "The Gold price hit 2500 USD and EUR COT showed 150k Net Long positions.",
        "scratchpad": [
            "### TOOL OUTPUT: price_data ###\nGold Price: 2150.45 USD\n",
            "### TOOL OUTPUT: cot_data ###\nEUR COT: 80k Net Long\n"
        ],
        "fact_check_result": None
    }
    
    print("\n--- Running node_fact_checker ---")
    result = await agent.node_fact_checker(mock_state)
    
    audit = result.get("fact_check_result", {})
    print(f"Audit Status: {audit.get('status')}")
    print(f"Discrepancies found: {audit.get('discrepancies')}")
    
    if audit.get("status") == "FAIL" and len(audit.get("discrepancies", [])) > 0:
        print("✅ SUCCESS: Fact-checker caught the hallucinations (2500 vs 2150 and 150k vs 80k).")
    else:
        print("❌ FAILURE: Fact-checker missed the discrepancies.")

if __name__ == "__main__":
    asyncio.run(verify())
