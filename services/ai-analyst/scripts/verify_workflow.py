import asyncio
import sys
from pathlib import Path

# Add parent dir to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.agents.supervisor import SupervisorAgent
from app.agents.strategy_advisor import StrategyAdvisorAgent
from app.core.workflow import AgentState
from langchain_core.messages import HumanMessage

async def verify_workflow():
    print("🧪 Starting AI Workflow Verification...")
    
    # 1. Initialize Services
    try:
        gemini = GeminiClient()
        rag = RAGService(gemini)
        supervisor = SupervisorAgent(gemini)
        advisor = StrategyAdvisorAgent(rag, gemini)
        print("✅ Services Initialized")
    except Exception as e:
        print(f"❌ Service Init Failed: {e}")
        return

    # 2. Test Supervisor Routing
    print("\n🔍 Testing Supervisor Routing...")
    state: AgentState = {
        "messages": [HumanMessage(content="I need help writing a Moving Average Crossover strategy.")],
        "user_id": "test_user",
        "user_config": {},
        "context": {},
        "scratchpad": []
    }
    
    state = await supervisor.route(state)
    print(f"Supervisor Decision: {state.get('next_node')}")
    
    if state.get("next_node") == "StrategyAdvisor":
        print("✅ Supervisor correctly routed to StrategyAdvisor")
    else:
        print(f"❌ Supervisor Routing Failed: {state.get('next_node')}")

    # 3. Test Strategy Advisor (Mocking RAG for speed if needed, but we rely on real RAG)
    print("\n🧠 Testing Strategy Advisor (CoT)...")
    
    # Mocking a file upload context
    state["context"]["file_context"] = None 
    
    try:
        state = await advisor.run(state)
        response = state.get("final_response")
        if response and "def" in response:
            print("✅ Strategy Advisor generated code:")
            print(response[:200] + "...")
        else:
            print("❌ Strategy Advisor failed to generate code.")
            print(f"Scratchpad: {state.get('scratchpad')}")
            
    except Exception as e:
         print(f"❌ Strategy Advisor Error: {e}")

    print("\n🎉 Verification Complete.")

if __name__ == "__main__":
    asyncio.run(verify_workflow())
