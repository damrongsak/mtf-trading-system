from app.services.gemini import GeminiClient
from app.core.workflow import AgentState
import json

class SupervisorAgent:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client
        self.system_prompt = """
        You are the Supervisor of the MTF Olympus Trading System.
        Your job is to ROUTE user requests to the correct Specialist Agent.
        
        Available Agents:
        1. **StrategyAdvisor**: For coding, backtesting, python logic, creating strategies, fixing code.
        2. **MarketObserver**: For market analysis, price trends, "what is happening in XAUUSD", news, sentiment.
        3. **General**: For greeting, small talk, or questions unrelated to trading/coding.
        
        Output JSON ONLY:
        {
            "next_node": "StrategyAdvisor" | "MarketObserver" | "General",
            "reasoning": "User is asking about code..."
        }
        """

    async def route(self, state: AgentState) -> AgentState:
        """Decides the next node based on the last message."""
        last_message = state["messages"][-1].content
        
        # Use BYOK config if present
        api_key = state.get("user_config", {}).get("api_key")
        model_id = state.get("user_config", {}).get("model_id")

        prompt = f"{self.system_prompt}\n\nUser Message: {last_message}"
        
        try:
            # We use a lightweight call here. 
            # Note: We duplicate logic from GeminiClient temporarily or expose a raw method
            # Ideally GeminiClient should have a 'generate_raw'
            # Ideally GeminiClient should have a 'generate_raw'
            client = self.gemini.client
            if api_key:
                # Use the factory from the injected gemini instance
                client = self.gemini.client_factory(api_key=api_key)
            
            response = await client.aio.models.generate_content(
                model=model_id or self.gemini.model_id,
                contents=prompt
            )
            
            text = response.text.strip()
            # Clean possible markdown code blocks
            if text.startswith("```json"):
                text = text[7:-3]
            
            decision = json.loads(text)
            state["next_node"] = decision.get("next_node", "General")
            state["scratchpad"].append(f"Supervisor routed to {state['next_node']}: {decision.get('reasoning')}")
            
        except Exception as e:
            state["next_node"] = "General"
            state["scratchpad"].append(f"Supervisor failed, defaulting to General. Error: {e}")
            
        return state
