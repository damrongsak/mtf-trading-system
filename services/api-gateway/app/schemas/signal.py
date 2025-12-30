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
    broker: Optional[str] = None
    strategy_name: Optional[str] = None
    confidence: Optional[float] = 0.0
    
    class Config:
        from_attributes = True

class SignalRequest(BaseModel):
    symbol: str
    timeframe: str = "15m"

class SignalBatchRequest(BaseModel):
    broker: str = "OANDA"
    strategy_id: str = "system_default"

