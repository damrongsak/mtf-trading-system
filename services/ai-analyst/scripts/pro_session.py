import asyncio
import sys
import argparse
import json
import logging
from pathlib import Path
import aiohttp

# Add parent dir to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.gemini import GeminiClient
from app.services.rag import RAGService
from app.agents.supervisor import SupervisorAgent
from app.agents.strategy_advisor import StrategyAdvisorAgent
from app.core.workflow import AgentState, registry
from langchain_core.messages import HumanMessage

# Configure Logging
logging.basicConfig(level=logging.ERROR)
# logger = logging.getLogger(__name__)

async def get_auth_token(username, password):
    """Authenticates to get a Bearer token."""
    base_url = settings.API_GATEWAY_URL
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{base_url}/api/v1/auth/token", data={"username": username, "password": password}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return f"Bearer {data['auth']['access_token']}"
        except Exception as e:
            print(f"⚠️  Auth Connection Warning: {e}")
    return None

# --- Mock Tools for Pro Session ---
async def list_active_strategies(user_id: str):
    """Mocks fetching active strategies from Strategy Core."""
    # In a real app, this would call API Gateway -> Strategy Core
    return [
        {"id": "strat_123", "name": "TrendFollow_XAU", "type": "ALPHA_ENGINE_V1", "status": "ACTIVE"}
    ]

async def deploy_alpha_strategy(user_id: str, symbol: str, formula: str, **kwargs):
    """Mocks deploying a strategy."""
    print(f"\n🚀 [SYSTEM] Deploying Strategy for {user_id}:")
    print(f"   Symbol: {symbol}")
    print(f"   Formula: {formula}")
    print(f"   Params: {kwargs}")
    return {"status": "success", "deployment_id": "deploy_999", "message": "Strategy deployed to Execution Engine."}

async def main():
    parser = argparse.ArgumentParser(description="MTF Olympus Pro AI Interface")
    parser.add_argument("--username", type=str, default="trader1", help="Username")
    parser.add_argument("--password", type=str, default="password123", help="Password")
    args = parser.parse_args()

    print("\n🔮 Initializing MTF Olympus Pro AI...\n")

    # 1. Auth
    token = await get_auth_token(args.username, args.password)
    user_id = args.username # simplistic
    if token:
        print(f"✅ Authenticated as '{args.username}'")
    else:
        print(f"⚠️  Running in Offline Mode (No API Access)")

    # 2. Initialize Services
    try:
        gemini = GeminiClient()
        rag = RAGService(gemini_client=gemini)
        print("✅ Connected to Gemini 2.5 & Qdrant RAG")
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        return

    # 3. Initialize Agents
    supervisor = SupervisorAgent(gemini)
    advisor = StrategyAdvisorAgent(rag_service=rag, gemini_client=gemini)

    # 4. Register Tools
    registry.register("list_active_strategies", list_active_strategies)
    registry.register("deploy_alpha_strategy", deploy_alpha_strategy)

    print("\n✨ System Ready. Available Experts:")
    print("   1. Strategy Advisor (Coding, Backtesting, Deployment)")
    print("   2. Market Observer (News, Sentiment - *Coming Soon*)")
    print("\nType your request (e.g., 'Create a mean reversion strategy for Gold') or 'exit'.\n")

    # 5. Interactive Loop
    while True:
        try:
            user_input = input(">> ")
            if user_input.lower() in ["exit", "quit"]:
                break
            if not user_input.strip():
                continue

            # --- Workflow Execution ---
            
            # A. Initialize State
            state = AgentState(
                messages=[HumanMessage(content=user_input)],
                user_id=user_id,
                user_config={"api_key": None, "model_id": None},
                context={},
                scratchpad=[],
                summary=None,
                next_node=None,
                final_response=None
            )

            # B. Supervisor Routing
            print("Thinking...", end="", flush=True)
            state = await supervisor.route(state)
            print(f"\r[Supervisor] Routing to: {state['next_node']}")

            # C. Expert Execution
            if state["next_node"] == "StrategyAdvisor":
                state = await advisor.run(state)
                
                # Output
                if state.get("final_response"):
                    print("\n" + "-"*50)
                    print(state["final_response"])
                    print("-"*(50) + "\n")
                elif state["scratchpad"]:
                    # Fallback if no final response but work was done
                    print("\n[Scratchpad Output]:\n" + state["scratchpad"][-1])

            elif state["next_node"] == "MarketObserver":
                print("\n[MarketObserver] Logic not fully implemented in CLI yet. Try 'Daily Briefing'.\n")
            
            else:
                print("\n[General] Hello! I am here to help with trading logic. Please ask about strategies.\n")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    asyncio.run(main())
