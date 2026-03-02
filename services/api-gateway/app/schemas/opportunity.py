from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
import uuid


class OpportunityLogResponse(BaseModel):
    """Response schema for a single opportunity log entry."""

    id: uuid.UUID
    timestamp: Optional[datetime] = None
    symbol: str
    timeframe: Optional[str] = "H1"
    direction: str
    strategy_name: Optional[str] = None
    filter_name: str
    filter_value: Optional[float] = None
    threshold_value: Optional[float] = None
    reason: Optional[str] = None
    meta_data: Optional[Any] = None

    model_config = {"from_attributes": True}
