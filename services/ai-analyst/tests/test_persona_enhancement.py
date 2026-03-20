import asyncio
import pytest
from unittest.mock import AsyncMock, patch
import json
import sys
import os

# Set PYTHONPATH to /app so 'app' package is found when running in container
os.environ["PYTHONPATH"] = "/app"
sys.path.append("/app")

from app.agents.strategy_advisor import StrategyAdvisorAgent
from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.services.memory import MemoryService
from langchain_core.messages import HumanMessage

async def test_persona_injection():
    """
    Verifies that the new SYSTEM_PERSONA with identity protection
    and Thai language protocols is correctly injected into the final generation prompt.
    """
    mock_rag = AsyncMock(spec=RAGService)
    mock_gemini = AsyncMock(spec=GeminiClient)
    mock_memory = AsyncMock(spec=MemoryService)
    
    # We want to capture the prompt sent to node_generate
    captured_prompts = []
    
    async def capture_side_effect(model=None, contents=None, **kwargs):
        prompt = contents[0] if isinstance(contents, list) else str(contents)
        captured_prompts.append(prompt)
        print(f"--- Captured Prompt (First 100 chars) ---\n{prompt[:100]}...")
        
        # Responses for various nodes
        if "optimized_query" in prompt:
            return {"text": '{"optimized_query": "สวัสดี คุณคือใคร", "intent": "CHAT", "target_language": "Thai"}'}
        if "severity" in prompt:
            return {"text": '{"severity": "ROUTINE", "rationale": "ok"}'}
        if "is_satisfactory" in prompt:
            return {"text": '{"is_satisfactory": true, "feedback": ""}'}
        if "next_node" in prompt or "ROUTE" in prompt:
             return {"text": '{"next_node": "generate", "intent": "CHAT", "severity": "ROUTINE", "reasoning": "direct"}'}
        
        return {"text": "Final Thai Response"}

    mock_gemini.generate_content.side_effect = capture_side_effect
    # Also mock internal client for any direct calls
    mock_gemini.client = AsyncMock()
    
    advisor = StrategyAdvisorAgent(
        mock_rag, 
        mock_gemini, 
        memory_service=mock_memory
    )
    
    # Run the graph
    print("Running advisor...")
    try:
        # StrategyAdvisorAgent.run(input_text, user_id, ...)
        # We need to provide all required args or default them in advisor.run
        # The run method starts the graph from query_optimizer.
        result = await advisor.run(
            input_text="สวัสดี คุณคือใคร", 
            user_id="test_user"
        )
        print(f"Result received: {result.get('response', '')[:50]}...")
    except Exception as e:
        print(f"Graph execution failed: {e}")
        import traceback
        traceback.print_exc()
        raise e
    
    # Check if any captured prompt contains the new identity strings
    found_identity = False
    found_thai_protocol = False
    
    print(f"Total prompts captured: {len(captured_prompts)}")
    for i, p in enumerate(captured_prompts):
        if "MTF Olympus" in p and 'NOT "Project Olympus" by Microsoft' in p:
            found_identity = True
            print(f"✅ Found identity protection in prompt #{i}")
        if "Thai Logic" in p and "translate your entire response" in p:

            found_thai_protocol = True
            print(f"✅ Found Thai language protocol in prompt #{i}")
            
    if not found_identity:
        print("❌ Identity protection NOT found in any prompt.")
        # Print a sample of the prompts to see what's in there
        for i, p in enumerate(captured_prompts):
             print(f"--- Prompt #{i} Snippet ---\n{p[:500]}...")
            
    assert found_identity, "Identity protection not found in prompt"
    assert found_thai_protocol, "Thai language protocol not found in prompt"
    print("\n✅ Persona Injection Verified.")

if __name__ == "__main__":
    asyncio.run(test_persona_injection())
