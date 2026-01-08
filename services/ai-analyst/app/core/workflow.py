from typing import TypedDict, List, Dict, Any, Optional, Union
from typing_extensions import Annotated
import operator
from langchain_core.messages import BaseMessage
from app.services.gemini import GeminiClient

# --- State Definition (The "Wire") ---
class UserConfig(TypedDict):
    api_key: Optional[str]
    model_id: Optional[str]

class AgentState(TypedDict):
    """
    Standardized State passed between nodes in the Olympus Workflow.
    similar to n8n's JSON flow context.
    """
    messages: Annotated[List[BaseMessage], operator.add]
    user_id: str
    user_config: UserConfig
    
    # Context (RAG results, File content)
    context: Dict[str, Any]
    
    # Reasoning Trace (CoT)
    scratchpad: List[str]
    
    # Context Management
    summary: Optional[str] # Long-term conversation summary
    
    # Decisions
    next_node: Optional[str]
    final_response: Optional[str]

# --- Tool Registry (The "Node" Library) ---
class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, name: str, func: callable):
        self._tools[name] = func

    def get(self, name: str):
        return self._tools.get(name)

    async def execute(self, name: str, **kwargs):
        if name not in self._tools:
            raise ValueError(f"Tool {name} not found")
        return await self._tools[name](**kwargs)

# Global Registry Instance
registry = ToolRegistry()

# --- Workflow Base ---
class OlympusWorkflow:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini
        self.registry = registry

    async def run_node(self, state: AgentState) -> AgentState:
        """Override this in subclasses"""
        raise NotImplementedError
