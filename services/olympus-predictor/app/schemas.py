from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PredictionRequest(BaseModel):
    symbol: str = "XAUUSD"
    steps: int = 5
    
class PredictionResponse(BaseModel):
    symbol: str
    forecast_date: datetime
    predictions: List[float]
    confidence_intervals: Optional[List[List[float]]] = None
    model_version: str
    breakdown: dict # {linear: [], residual: []}

class TrainingResponse(BaseModel):
    status: str
    metrics: dict # {mae: float, rmse: float}
    trained_at: datetime
