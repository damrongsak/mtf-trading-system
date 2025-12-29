from pydantic import BaseModel
from typing import Optional

class StrategyChatRequest(BaseModel):
    message: str
    user_id: str
    strategy_id: Optional[str] = None
    context_code: Optional[str] = None
    context_stats: Optional[dict] = None # e.g. Backtest results
    image_b64: Optional[str] = None # Base64 encoded image

