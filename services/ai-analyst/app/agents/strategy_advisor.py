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
        
        # 2. Reason & Plan (CoT)
        state = await self.reason_and_plan(state, user_query, doc_text, strat_text, file_context)
        
        # 3. Generate Code
        state = await self.generate_code(state, doc_text)
        
        return state

    async def reason_and_plan(self, state, query, docs, strats, file_context) -> AgentState:
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
