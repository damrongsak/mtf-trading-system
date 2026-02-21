from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class PredictionRequest(BaseModel):
    symbol: str = "XAUUSD"
    steps: int = 5

class PredictionResponse(BaseModel):
    symbol: str
    forecast_date: datetime
    predictions: List[float]
    model_version: str
    breakdown: Dict[str, Any]

class TrainingResponse(BaseModel):
    status: str
    metrics: Dict[str, Any]
    trained_at: datetime
