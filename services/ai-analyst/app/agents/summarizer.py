from app.core.workflow import AgentState, OlympusWorkflow
from asyncio import sleep

class SummarizerAgent(OlympusWorkflow):
    async def run(self, state: AgentState) -> AgentState:
        """
        Condenses the conversation history into a running summary.
        Keeps the last N messages intact.
        """
        messages = state["messages"]
        current_summary = state.get("summary", "")
        
        # Thresholds
        KEEP_LAST = 5
        
        if len(messages) <= KEEP_LAST:
            return state
            
        # Messages to summarize (all except last N)
        to_summarize = messages[:-KEEP_LAST]
        recent_messages = messages[-KEEP_LAST:]
        
        conversation_text = "\n".join([f"{m.type}: {m.content}" for m in to_summarize])
        
        prompt = f"""
        Progressively summarize the following conversation.
        
        Current Summary:
        {current_summary or "None"}
        
        New Lines to Add:
        {conversation_text}
        
        Output a concise paragraph updating the summary with the new information.
        Retain key technical details (strategies discussed, errors found, user preferences).
        """
        
        try:
            client = self.gemini.client
            # Handle BYOK if configured
            api_key = state.get("user_config", {}).get("api_key")
            if api_key:
                client = self.gemini.client_factory(api_key=api_key)

            response = await client.aio.models.generate_content(
                model=state.get("user_config", {}).get("model_id") or self.gemini.model_id,
                contents=prompt
            )
            
            new_summary = response.text
            
            # Update State
            state["summary"] = new_summary
            # Prune messages (keep summary + recent)
            # Note: We can't easily "replace" the list in LangGraph if using operator.add blindly, 
            # but for this customized state we act on the object directly if not strictly using compiled graph.
            # Assuming we return the full state to be respected.
            state["messages"] = recent_messages 
            state["scratchpad"].append("Context summarized to save tokens.")
            
        except Exception as e:
            state["scratchpad"].append(f"Summarization failed: {e}")
            
        return state
