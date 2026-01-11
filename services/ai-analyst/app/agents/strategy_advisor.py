from app.core.workflow import AgentState, OlympusWorkflow
from app.services.rag import RAGService
from app.services.gemini import GeminiClient
import json

class StrategyAdvisorAgent(OlympusWorkflow):
    def __init__(self, rag_service: RAGService, gemini_client: GeminiClient):
        super().__init__(gemini_client)
        self.rag = rag_service
        
    async def run(self, state: AgentState) -> AgentState:
        """
        Main entry point for the Strategy workflow.
        Steps: Retrieve -> Reason -> Generate Code -> Validate
        """
        # 1. Retrieve Context
        user_query = state["messages"][-1].content
        user_id = state["user_id"]
        
        # Check for user file context
        file_context = state.get("context", {}).get("file_context")
        
        # Retrieve System Docs
        docs = await self.rag.search_documentation(user_query)
        doc_text = "\n".join([f"[{d['filename']}]: {d['content'][:500]}..." for d in docs])
        
        # Retrieve Similar Strategies
        strategies = await self.rag.search_similar_strategies(user_query, user_id=user_id)
        strat_text = "\n".join([s['code'][:300] for s in strategies])
        
        # Retrieve Similar Strategies
        strategies = await self.rag.search_similar_strategies(user_query, user_id=user_id)
        strat_text = "\n".join([s['code'][:300] for s in strategies])
        
        # Retrieve Active Strategies (Context Awareness)
        active_strats = await self.registry.execute("list_active_strategies", user_id=user_id)
        active_context = json.dumps(active_strats, indent=2)
        
        # 2. Reason & Plan (CoT)
        state = await self.reason_and_plan(state, user_query, doc_text, strat_text, active_context, file_context)
        
        # 3. Execute Action (Generate Code OR Deploy)
        # Check plan for intent
        last_plan = state["scratchpad"][-1]
        
        if "ACTION: DEPLOY" in last_plan:
            state = await self.deploy_strategy(state)
        else:
            # Default to Code Gen (Backtest/Research)
            state = await self.generate_code(state, doc_text)
        
        return state

    async def reason_and_plan(self, state, query, docs, strats, active_context, file_context) -> AgentState:
        api_key = state.get("user_config", {}).get("api_key")
        model_id = state.get("user_config", {}).get("model_id")

        multimodal_content = []
        prompt_text = f"""
        You are an expert Quant Developer for the MTF Olympus System.
        
        Session Summary:
        {state.get("summary", "None")}
        
        User Request: "{query}"

        Knowledge Base:
        {docs}

        Similar Strategies:
        {strats}
        
        Analyze the request and creating a step-by-step implementation plan.
        If the user provided a file (Chart/PDF), use it to extract logic.

        # Context Awareness
        The user currently has these active strategies:
        {active_context}
        Check if the request duplicates an existing one. If so, mention it.

        # Tools & Actions
        You have two capabilities:
        1. GENERATE CODE: For backtesting in vectorbt (Python).
        2. DEPLOY STRATEGY: For launching a live Alpha Engine strategy.

        If the user explicitly asks to "Deploy", "Start", "Trade", or "Launch" a strategy:
        - Output the line "ACTION: DEPLOY" at the end of your plan.
        - Specify the Formula and Thresholds clearly in a JSON block labeled "DEPLOY_PAYLOAD".
        
        DEPLOY_PAYLOAD Schema:
        {{
            "symbol": "XAU/USD",
            "formula": "...",
            "threshold_long": 30.0,
            "threshold_short": 70.0,
            "strategy_type": "ALPHA_ENGINE_V1" (or "HYBRID_ALPHA_V1"),
            "description": "Concise explanation of intent"
        }}

        IMPORTANT: If the user asks for a specific factor or signal formula, use the 'Alpha Engine' syntax:
        - Format: Single line expression string.
        - Supported Functions:
            - rank(series): Cross-sectional rank (0.0 to 1.0)
            - delay(series, n): Lag series by n periods
            - ts_max(series, n): Rolling max over n periods
            - ts_min(series, n): Rolling min over n periods
            - ts_argmax(series, n): Index of max
            - correlation(s1, s2, n): Rolling correlation
            - sma(series, n): Simple Moving Average
            - std(series, n): Rolling Std Dev
            - log(series): Natural log
            - sign(series): Sign of value (-1, 0, 1)
        - Inputs: 'open', 'high', 'low', 'close', 'volume'
        - Examples:
            - Momentum: "rank(close / delay(close, 5))"
            - Mean Reversion: "-1 * correlation(close, delay(close, 1), 5)"
            - Breakout: "(close - ts_min(low, 20)) / (ts_max(high, 20) - ts_min(low, 20))"
        """
        multimodal_content.append(prompt_text)

        # Attach file if present
        if file_context and file_context.get("type") == "base64":
            import base64
            img_data = base64.b64decode(file_context["data"])
            multimodal_content.append({
                "mime_type": file_context["mime_type"],
                "data": img_data
            })
            prompt_text += "\n[Attached File Analysis Required]"

        try:
             # Transient client for BYOK
            client = self.gemini.client
            if api_key:
                from google import genai
                client = genai.Client(api_key=api_key)

            response = await client.aio.models.generate_content(
                model=model_id or self.gemini.model_id,
                contents=multimodal_content
            )
            state["scratchpad"].append(f"Plan: {response.text}")
        except Exception as e:
            state["scratchpad"].append(f"Error planning: {e}")
            
        return state

    async def generate_code(self, state, docs) -> AgentState:
        api_key = state.get("user_config", {}).get("api_key")
        model_id = state.get("user_config", {}).get("model_id")
        
        plan = state["scratchpad"][-1]
        
        prompt = f"""
        Based on this plan:
        {plan}
        
        And these system docs:
        {docs}
        
        Write the compatible Python code (vectorbt/pandas).
        Ensure it follows the 'SandboxedStrategy' class structure if applicable.
        Output ONLY the code block.
        """
        
        try:
            client = self.gemini.client
            if api_key:
                from google import genai
                client = genai.Client(api_key=api_key)

            response = await client.aio.models.generate_content(
                model=model_id or self.gemini.model_id,
                contents=prompt
            )
            code = response.text.replace("```python", "").replace("```", "")
            state["final_response"] = code
        except Exception as e:
             state["final_response"] = f"Error generating code: {e}"
             
        return state

    async def deploy_strategy(self, state) -> AgentState:
        """
        Parses the plan for DEPLOY_PAYLOAD and calls the alpha_deployer tool.
        """
        plan = state["scratchpad"][-1]
        user_id = state["user_id"]
        
        try:
            # Extract JSON payload
            import re
            json_match = re.search(r'DEPLOY_PAYLOAD.*?({.*})', plan, re.DOTALL)
            if json_match:
                payload_str = json_match.group(1)
                payload = json.loads(payload_str)
                
                # Call Tool
                result = await self.registry.execute("deploy_alpha_strategy", 
                    user_id=user_id,
                    symbol=payload.get("symbol"),
                    formula=payload.get("formula"),
                    threshold_long=payload.get("threshold_long"),
                    threshold_short=payload.get("threshold_short"),
                    strategy_type=payload.get("strategy_type", "ALPHA_ENGINE_V1"),
                    description=payload.get("description", "")
                )
                
                state["final_response"] = f"Deployment Action Executed:\n{result}"
            else:
                state["final_response"] = "Error: Could not parse DEPLOY_PAYLOAD from plan. Please try again."
                
        except Exception as e:
            state["final_response"] = f"Error executing deployment: {e}"
            
        return state
