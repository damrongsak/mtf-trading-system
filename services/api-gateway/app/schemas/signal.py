from pydantic import BaseModel
from typing import Optional

class SignalRequest(BaseModel):
    symbol: str
    timeframe: str

class SignalResponse(BaseModel):
    allowed: bool
    reason: str
