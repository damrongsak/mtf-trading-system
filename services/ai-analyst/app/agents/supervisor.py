from app.services.gemini import GeminiClient
from app.core.workflow import AgentState
import json

class SupervisorAgent:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client
        self.system_prompt = """
        You are the Supervisor of the MTF Olympus Trading System.
        Your job is to ROUTE user requests to the correct Specialist Agent based on Intent and Market Severity.
        
        Available Specialists:
        1. **StrategyAdvisor**: For coding, backtesting, strategy optimization, and DAILY BRIEFINGS.
        2. **MarketObserver**: For real-time market analysis, news sentiment, and "what is happening" queries.
        3. **General**: For greetings, system status, or non-trading questions.
        
        Intents to recognize:
        - `briefing`: Morning/Daily briefings.
        - `analysis`: Technical/SMC market analysis.
        - `optimization`: Strategy parameter tuning.
        - `chat`: General trading discussion.

        Output JSON ONLY:
        {
            "next_node": "StrategyAdvisor" | "MarketObserver" | "General",
            "intent": "briefing" | "analysis" | "optimization" | "chat" | "general",
            "severity": "ROUTINE" | "VOLATILITY" | "CRISIS",
            "reasoning": "User is asking about..."
        }
        """

    async def route(self, state: AgentState) -> AgentState:
        """Decides the next node based on the last message and market context."""
        last_message = state["messages"][-1].content
        
        # Check for market context in scratchpad or state if injected by earlier nodes
        # If not, we might need a dedicated market_context_node before supervisor
        market_severity = state.get("market_severity", "ROUTINE")

        # Use BYOK config if present
        api_key = state.get("user_config", {}).get("api_key")
        model_id = state.get("user_config", {}).get("model_id")

        prompt = f"{self.system_prompt}\n\nCurrent Market Severity: {market_severity}\nUser Message: {last_message}"
        
        try:
            client = self.gemini.client
            if api_key:
                client = self.gemini.client_factory(api_key=api_key)
            
            response = await client.aio.models.generate_content(
                model=model_id or self.gemini.model_id,
                contents=prompt
            )
            
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3]
            
            decision = json.loads(text)
            state["next_node"] = decision.get("next_node", "General")
            state["scratchpad"].append(f"Supervisor routed to {state['next_node']} (Intent: {decision.get('intent')}, Severity: {decision.get('severity')}): {decision.get('reasoning')}")
            
            # Persist intent and severity in state
            state["intent"] = decision.get("intent", "general")
            # If AI says CRISIS, but market says ROUTINE, we might want to override or vice-versa
            # For now, trust the AI classification which combines both
            state["market_severity"] = decision.get("severity", market_severity)
            
        except Exception as e:
            state["next_node"] = "General"
            state["scratchpad"].append(f"Supervisor failed, defaulting to General. Error: {e}")
            
        return state
