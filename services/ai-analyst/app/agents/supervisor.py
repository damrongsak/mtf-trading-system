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
        1. **StrategyAdvisor**: For coding, backtesting, strategy optimization, and DAILY BRIEFINGS. Also handles proprietary architecture/API questions (set intent to `ABOUT_SYSTEM`).
        2. **MarketObserver**: For real-time market analysis, news sentiment, and "what is happening" queries.
        3. **RiskRebalancer**: For dynamic drawdown adjustments, risk rebalancing, and portfolio safety reviews.
        4. **General**: For greetings, system status, or non-trading questions.
        
        Intents to recognize:
        - `briefing`: Morning/Daily briefings.
        - `analysis`: Technical/SMC market analysis.
        - `optimization`: Strategy parameter tuning.
        - `rebalance`: Risk rebalancing or drawdown threshold adjustments.
        - `ABOUT_SYSTEM`: Use for any questions regarding MTF Olympus proprietary tools, API endpoints, internal architecture, or if the user mentions "EA", "Legend EA", or "Project Olympus".
        - `chat`: General trading discussion.

        Output JSON ONLY:
        {
            "next_node": "StrategyAdvisor" | "MarketObserver" | "RiskRebalancer" | "General",
            "intent": "briefing" | "analysis" | "optimization" | "rebalance" | "ABOUT_SYSTEM" | "chat" | "general",
            "severity": "ROUTINE" | "VOLATILITY" | "CRISIS",
            "block_web_search": true | false,
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
            # If intent is ABOUT_SYSTEM, force block_web_search if not specified
            state["block_web_search"] = decision.get("block_web_search", decision.get("intent") == "ABOUT_SYSTEM")
            
            # If AI says CRISIS, but market says ROUTINE, we might want to override or vice-versa
            # For now, trust the AI classification which combines both
            state["market_severity"] = decision.get("severity", market_severity)

            
        except Exception as e:
            state["next_node"] = "General"
            state["scratchpad"].append(f"Supervisor failed, defaulting to General. Error: {e}")
            
        return state
