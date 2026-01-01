from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.generated import FoundryAssembleRequest, APIResponse_FoundryAssembleResponse
from app.models.strategy_config import StrategyConfig
from app.models.user_fund import User
from app.security import get_current_user
import httpx
import os
import json

router = APIRouter(prefix="/foundry", tags=["foundry"])

STRATEGY_CORE_URL = os.getenv("STRATEGY_CORE_URL", "http://strategy-core:8000")

@router.post("/assemble", response_model=APIResponse_FoundryAssembleResponse)
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
                return APIResponse_FoundryAssembleResponse(
                    status="error",
                    data={"pipeline_hash": "", "errors": [f"Strategy Core Error: {resp.text}"]}
                )
            
            data = resp.json() 
            # Strategy Core returns {pipeline_hash: ..., errors: []}
            
            return APIResponse_FoundryAssembleResponse(
                status="success",
                data=data
            )

    except Exception as e:
         return APIResponse_FoundryAssembleResponse(
            status="error",
            data={"pipeline_hash": "", "errors": [str(e)]}
        )
