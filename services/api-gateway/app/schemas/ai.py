from pydantic import BaseModel
from typing import List, Optional

class MarketAnalysisRequest(BaseModel):
    trend_4h: str
    current_price: float
    key_levels: List[float] = []
    recent_signals: List[dict] = []
    
class JournalAnalysisRequest(BaseModel):
    entry_content: str
    entry_id: Optional[str] = None

class AnalysisResponse(BaseModel):
    insight: str
    timestamp: str
