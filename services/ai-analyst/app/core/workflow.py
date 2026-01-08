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
        self._tools: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict] = {}

    def register(self, name: str, tool: Any, description: str = ""):
        """Register a tool instance or callable."""
        self._tools[name] = tool
        
        # Extract metadata if available (LangChain BaseTool)
        desc = description
        args = {}
        
        if hasattr(tool, "description") and not desc:
            desc = tool.description
        if hasattr(tool, "args"):
            args = tool.args
            
        self._metadata[name] = {
            "name": name,
            "description": desc,
            "args": args
        }

    def get(self, name: str) -> Any:
        return self._tools.get(name)
        
    def list_tools(self) -> List[Dict]:
        """Return list of available tools for UI."""
        return list(self._metadata.values())

    async def execute(self, name: str, **kwargs):
        if name not in self._tools:
            raise ValueError(f"Tool {name} not found")
        
        tool = self._tools[name]
        
        # Handle LangChain BaseTool
        if hasattr(tool, "ainvoke"):
            return await tool.ainvoke(kwargs)
        elif hasattr(tool, "invoke"):
            # Fallback for sync tools if needed, but perform strictly async here ideally
            return tool.invoke(kwargs)
            
        # Handle simple callable
        return await tool(**kwargs)

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
