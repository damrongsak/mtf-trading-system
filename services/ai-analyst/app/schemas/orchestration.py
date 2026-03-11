from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class Severity(str, Enum):
    ROUTINE = "ROUTINE"
    VOLATILITY = "VOLATILITY"
    CRISIS = "CRISIS"

class AIThinkRequest(BaseModel):
    message: str = Field(..., description="User input or command")
    intent: Optional[str] = Field(None, description="Optional hint for the orchestrator (e.g. 'briefing', 'market_analysis')")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional dynamic context (deployment_id, strategy_id, symbol)")
    image_b64: Optional[str] = Field(None, description="Optional base64 encoded image for multimodal analysis")
    thread_id: Optional[str] = Field(None, description="Optional LangGraph thread ID for persistence")

class AIThinkResponse(BaseModel):
    response: str = Field(..., description="Final narrative or data from the AI")
    intent_resolved: Optional[str] = None
    severity: Severity = Severity.ROUTINE
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)
