from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"

class SignalResponse(BaseModel):
    symbol: str
    timeframe: str
    timestamp: datetime
    direction: SignalDirection
    entry_price: float
    sl_price: float
    tp_price: float
    reason: Optional[str] = None
    
    class Config:
        from_attributes = True

class SignalRequest(BaseModel):
    symbol: str
    timeframe: str = "15m"
