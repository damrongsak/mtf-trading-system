from fastapi import APIRouter, HTTPException, Depends
from app.schemas.trade import RiskCheckRequest, RiskCheckResponse
from app.schemas.response import APIResponse
from app.utils.response import success_response
from app.security import get_current_user
from app.models.user import User
import httpx
import os

from app.utils.http_client import get_internal_client

router = APIRouter(
    prefix="/api/v1/risk",
    tags=["risk"]
)
EXECUTION_SERVICE_URL = os.getenv("EXECUTION_SERVICE_URL", "http://execution:8000")
STRATEGY_CORE_URL = os.getenv("STRATEGY_CORE_URL", "http://strategy-core:8000")

@router.post("/check", response_model=APIResponse[RiskCheckResponse])
async def check_risk(
    req: RiskCheckRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Proxy risk check to the Strategy Core Service.
    """
    async with await get_internal_client() as client:
        try:
            # Forward request to strategy-core service
            response = await client.post(
                f"{STRATEGY_CORE_URL}/api/v1/risk/check", 
                json=req.model_dump(mode='json'),
                timeout=5.0
            )
            response.raise_for_status()
            
            resp_data = response.json()
            # strategy-core returns {"data": {...}}
            if "data" in resp_data:
                return success_response(data=resp_data["data"])
            else:
                return success_response(data=resp_data)
                
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Risk service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Risk service error: {exc.response.text}")
