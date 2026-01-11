from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import httpx
import os
import logging

from app.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/alpha", tags=["alpha"])
logger = logging.getLogger(__name__)

STRATEGY_CORE_URL = os.getenv("STRATEGY_CORE_URL", "http://strategy-core:8000")

class AlphaRequest(BaseModel):
    formula: str
    symbol: str
    timeframe: str = "H1"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class AlphaResponse(BaseModel):
    signal: List[Optional[float]]
    metrics: Dict[str, Any]
    timestamps: List[datetime]

class APIResponseAlpha(BaseModel):
    status: str
    data: Optional[AlphaResponse] = None
    error: Optional[str] = None

@router.post("/test", response_model=APIResponseAlpha)
def test_alpha(
    req: AlphaRequest,
    current_user: User = Depends(get_current_user)
):
    return _proxy_request("test", req)

@router.post("/preview", response_model=APIResponseAlpha)
def preview_alpha(
    req: AlphaRequest,
    current_user: User = Depends(get_current_user)
):
    return _proxy_request("preview", req)

def _proxy_request(endpoint: str, req: AlphaRequest):
    try:
        url = f"{STRATEGY_CORE_URL}/api/v1/alpha/{endpoint}"
        payload = req.model_dump(mode='json')
        
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload)
            
            if resp.status_code != 200:
                logger.error(f"Strategy Core Error ({endpoint}): {resp.text}")
                return APIResponseAlpha(status="error", error=f"Engine Error: {resp.text}")
                
            data = resp.json()
            return APIResponseAlpha(status="success", data=data)
            
    except Exception as e:
        logger.error(f"Gateway Proxy Error: {e}")
        return APIResponseAlpha(status="error", error=str(e))
