---
name: manage-ai-analyst-agent
description: |
  Use this skill when you need to create, modify, or manage AI agents within the `ai-analyst` service.
  This includes adding new LangGraph nodes or entire agent workflows.
---

# Manage AI Analyst Agent
**Goal:** Create or modify an AI Agent in `services/ai-analyst/app/agents/`.

## Prerequisites
*   Identify the agent's purpose (e.g., "Risk Monitor", "News Analyst").
*   Determine the input/output state flow.

## Process

1.  **Create Agent File**
    *   Create a new file in `services/ai-analyst/app/agents/<agent_name>.py`.
    *   Inherit from `OlympusWorkflow` located in `app.core.workflow`.

2.  **Define Agent Logic**
    *   Implement the `async def run(self, state: AgentState) -> AgentState:` method.
    *   **State Access:** Access user query via `state["messages"][-1].content`.
    *   **Context:** Access RAG or tools via `self.registry`.
    *   **LLM Calls:** Use `self.gemini.client` (or `genai.Client` for BYOK) to generate content.

3.  **Update State**
    *   Append internal thoughts to `state["scratchpad"]`.
    *   Set the final user-facing answer in `state["final_response"]`.

4.  **Register the Agent**
    *   (If applicable for routing) Update the `SupervisorAgent` or entry point to route to this new agent.

## Code Template
```python
from app.core.workflow import AgentState, OlympusWorkflow
from app.services.gemini import GeminiClient

class MyNewAgent(OlympusWorkflow):
    def __init__(self, gemini_client: GeminiClient):
        super().__init__(gemini_client)

    async def run(self, state: AgentState) -> AgentState:
        # 1. Extract Input
        query = state["messages"][-1].content
        
        # 2. Reason / Call Tools
        # ... logic ...
        
        # 3. Generate Response
        response = await self.gemini.client.aio.models.generate_content(
            model=self.gemini.model_id,
            contents=f"Answer this: {query}"
        )
        
        # 4. Update State
        state["final_response"] = response.text
        return state
```

## Critical Rules
*   **State Immutability:** Do not mutate deeply nested objects in `state` if using parallel branches (LangGraph best practice), though currently `OlympusWorkflow` is linear.
*   **Error Handling:** Catch exceptions in `run()` and set `state["final_response"]` to an error message instead of crashing.
