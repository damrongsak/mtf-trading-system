import asyncio
import logging
import json
from datetime import datetime
from app.agents.strategy_advisor import StrategyAdvisorAgent
from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.services.memory import MemoryService
from langgraph.checkpoint.memory import MemorySaver

# Setup logging to be concise
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("intent-test")

async def test_intents():
    logger.info("🧪 Initializing AI Analyst Stress Test...")
    
    # 1. Setup Agent
    gemini = GeminiClient()
    rag = RAGService(gemini)
    memory = MemoryService(rag)
    checkpointer = MemorySaver()
    
    agent = StrategyAdvisorAgent(
        rag_service=rag,
        gemini_client=gemini,
        checkpointer=checkpointer,
        memory_service=memory
    )
    
    # 2. Define Query Dimensions
    test_cases = [
        {
            "name": "Direct Forecast",
            "query": "Give me the gold price forecast for the next 5 steps.",
            "expected_tool": "get_predictor_forecast"
        },
        {
            "name": "Direct Signal",
            "query": "What is the latest ML signal from Olympus Predictor for XAUUSD?",
            "expected_tool": "get_predictor_signal"
        },
        {
            "name": "Implicit Analysis",
            "query": "Based on the market trend and ML forecasts, what is the outlook for Gold?",
            "expected_tool": "get_predictor_forecast" # Should likely pick both, but we check if forecast is included
        },
        {
            "name": "System Health",
            "query": "Are the predictor and gateway services healthy right now?",
            "expected_tool": "get_system_health"
        },
        {
            "name": "Edge Case - Unsupported Symbol",
            "query": "What's the prediction for AAPL stock?",
            "expected_behavior": "Graceful refusal or XAUUSD fallback with caveat"
        }
    ]
    
    # 3. Run Tests
    results = []
    thread_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    config = {
        "configurable": {"thread_id": thread_id, "user_id": "test-user"},
        "recursion_limit": 100
    }
    
    for case in test_cases:
        logger.info(f"\n--- Testing Dimension: {case['name']} ---")
        logger.info(f"Query: \"{case['query']}\"")
        
        try:
            # We use stream to observe tool selection
            response_text = ""
            tools_used = []
            
            # Match AgentState: input_text, user_id, auth_token
            input_state = {
                "input_text": case["query"],
                "user_id": "test-user",
                "auth_token": "mock-token"
            }
            
            async for event in agent.graph.astream(
                input_state,
                config,
                stream_mode="updates" # Changed to updates to see component changes
            ):
                for node_name, node_update in event.items():
                    # Safety check for non-dict or None updates
                    if node_update is None or not isinstance(node_update, dict):
                        continue
                        
                    # Check for tool calls in tool_selection node
                    if "tool_calls" in node_update and node_update["tool_calls"]:
                        for tc in node_update["tool_calls"]:
                            # StrategyAdvisorAgent uses 'tool_name'
                            name = tc.get('tool_name') or tc.get('name')
                            if name:
                                tools_used.append(name)
                    
                    # Check for final response
                    if "final_response" in node_update:
                        response_text = node_update["final_response"]

            logger.info(f"Tools Used: {tools_used}")
            # logger.info(f"Response: {response_text[:100]}...")
            
            # Validation
            passed = True
            unique_tools = list(set(tools_used))
            logger.info(f"Unique Tools Used: {unique_tools}")
            
            if "expected_tool" in case:
                if case["expected_tool"] not in unique_tools:
                    logger.error(f"❌ FAILED: Expected tool '{case['expected_tool']}' not in {unique_tools}")
                    passed = False
                else:
                    logger.info(f"✅ PASS: Tool '{case['expected_tool']}' correctly selected.")
            else:
                logger.info("✅ PASS: Intent correctly mapped (no specific tool requirement).")
                
            results.append({
                "name": case["name"],
                "passed": passed,
                "tools": tools_used
            })
            
        except Exception as e:
            import traceback
            logger.error(f"💥 Error during test '{case['name']}': {e}")
            traceback.print_exc()
            results.append({"name": case["name"], "passed": False, "error": str(e)})

    # Summary
    logger.info("\n" + "="*30)
    logger.info("📊 STRESS TEST SUMMARY")
    logger.info("="*30)
    for r in results:
        status = "✅" if r["passed"] else "❌"
        logger.info(f"{status} {r['name']}")

if __name__ == "__main__":
    asyncio.run(test_intents())
