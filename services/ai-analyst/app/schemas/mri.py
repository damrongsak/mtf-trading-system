from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

class CoachingRequest(BaseModel):
    user_id: UUID
    lookback_days: int = 7
    focus_areas: List[str] = []

class CoachingResponse(BaseModel):
    psychological_state: str = Field(..., description="Detected emotional state (e.g., Revenge Trading, FOMO, Discipline)")
    advice: str = Field(..., description="Specific coaching narrative in Thai or English")
    confluence_context: Optional[dict] = None
    suggested_actions: List[str] = []
    sentiment_trend: Optional[str] = "STABLE"
