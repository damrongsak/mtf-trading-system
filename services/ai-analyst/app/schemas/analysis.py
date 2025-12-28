from pydantic import BaseModel
from typing import List, Optional, Any

class MarketAnalysisRequest(BaseModel):
    trend_4h: str
    current_price: float
    key_levels: List[float] = []
    recent_signals: List[dict] = []
    image_b64: Optional[str] = None
    
class JournalAnalysisRequest(BaseModel):
    entry_content: str
    entry_id: Optional[str] = None
    user_id: str # Required for RAG isolation

class AnalysisResponse(BaseModel):
    insight: str
    timestamp: str
