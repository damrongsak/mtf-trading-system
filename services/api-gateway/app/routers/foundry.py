from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.generated import FoundryAssembleRequest, APIResponseFoundryAssembleResponse
from pydantic import BaseModel
from typing import Dict, Any, List
from datetime import datetime

# Manually defining schemas to avoid regenerating everything right now
class WalkForwardRequest(BaseModel):
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    config: Dict[str, Any]

class WalkForwardResponse(BaseModel):
    robustness_score: int
    avg_sharpe_test: float
    details: List[Dict[str, Any]]

class APIResponse_WalkForwardResponse(BaseModel):
    status: str
    data: WalkForwardResponse
from app.models.strategy_config import StrategyConfig
from app.models.user_fund import User
from app.security import get_current_user
import httpx
import os
import json

router = APIRouter(prefix="/foundry", tags=["foundry"])

STRATEGY_CORE_URL = os.getenv("STRATEGY_CORE_URL", "http://strategy-core:8000")

@router.post("/assemble", response_model=APIResponseFoundryAssembleResponse)
def assemble_strategy(
    req: FoundryAssembleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Validate and Assemble a Strategy Config via Strategy Core.
    """
    try:
        # Proxy to Strategy Core
        # Strategy Core expects {'config': dict} which matches FoundryAssembleRequest
        
        # We need to construct the payload explicitly or just forward valid pydantic
        payload = req.model_dump()
        
        # Call Strategy Core
        # Strategy Core endpoint: /api/v1/foundry/assemble
        # (Assuming I mounted it with /api/v1 prefix in main.py)
        
        with httpx.Client() as client:
            resp = client.post(f"{STRATEGY_CORE_URL}/api/v1/foundry/assemble", json=payload)
            if resp.status_code != 200:
                return APIResponseFoundryAssembleResponse(
                    status="error",
                    data={"pipeline_hash": "", "errors": [f"Strategy Core Error: {resp.text}"]}
                )
            
            data = resp.json() 
            # Strategy Core returns {pipeline_hash: ..., errors: []}
            
            return APIResponseFoundryAssembleResponse(
                status="success",
                data=data
            )

    except Exception as e:
         return APIResponseFoundryAssembleResponse(
            status="error",
            data={"pipeline_hash": "", "errors": [str(e)]}
        )

@router.post("/validate", response_model=APIResponse_WalkForwardResponse)
def validate_strategy(
    req: WalkForwardRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Proxy to Strategy Core
        payload = req.model_dump(mode='json') # handle datetime serialization
        
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(f"{STRATEGY_CORE_URL}/api/v1/foundry/validate", json=payload)
            if resp.status_code != 200:
                 raise HTTPException(status_code=resp.status_code, detail=resp.text)
            
            data = resp.json()
            return APIResponse_WalkForwardResponse(
                status="success",
                data=data
            )
            
    except HTTPException:
        raise
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))
