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

class SMCRequest(BaseModel):
    open: List[float]
    high: List[float]
    low: List[float]
    close: List[float]

class SMCResponse(BaseModel):
    order_blocks: List[Dict[str, Any]]
    fvgs: List[Dict[str, Any]]
