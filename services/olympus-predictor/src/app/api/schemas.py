from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class PredictionRequest(BaseModel):
    symbol: str = "XAUUSD"
    steps: int = 5

class PredictionResponse(BaseModel):
    symbol: str
    forecast_date: datetime
    prices: List[float] # Updated to match predict output
    sigma_lr: List[float]
    model_version: str
    breakdown: Dict[str, Any]

class TrainRequest(BaseModel):
    symbol: str = "XAUUSD"
    lookback: int = 2000
    macro_lookback: int = 59

class TrainResponse(BaseModel):
    status: str
    message: str
    job_id: Optional[str] = None
    trained_at: datetime = datetime.now()

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    checked_at: datetime = datetime.now()

class SignalResponse(BaseModel):
    direction: str
    target: float
    stop_loss: float
    confidence: float
    sentiment_score: float
    timestamp: datetime = datetime.now()
