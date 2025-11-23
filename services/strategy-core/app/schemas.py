from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class IndicatorRequest(BaseModel):
    data: List[float]
    params: Dict[str, Any] = {}

class ATRRequest(BaseModel):
    high: List[float]
    low: List[float]
    close: List[float]
    window: int = 14

class IndicatorResponse(BaseModel):
    values: List[Optional[float]]
