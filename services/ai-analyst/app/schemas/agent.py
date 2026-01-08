from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class AgentConfig(BaseModel):
    """
    Configuration "Blueprint" for a Universal Agent.
    This schema determines how the agent behaves and what tools it can use.
    """
    name: str = Field(..., description="Display name of the agent (e.g. 'Risk Manager')")
    role: str = Field(..., description="System instruction / Persona defining the agent's behavior")
    model: str = Field("gemini-1.5-flash", description="LLM Model ID to use")
    tools: List[str] = Field(default_factory=list, description="List of tool names to enable for this agent")
    temperature: float = Field(0.1, ge=0.0, le=1.0, description="Creativity setting")
    
    # Metadata for UI
    description: Optional[str] = Field(None, description="Short description for the Agent Marketplace")
    avatar: Optional[str] = Field(None, description="Icon/Avatar filename")
