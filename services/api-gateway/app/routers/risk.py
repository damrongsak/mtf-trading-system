from fastapi import APIRouter, HTTPException
from app.schemas.trade import RiskCheckRequest, RiskCheckResponse
from app.schemas.response import APIResponse
from app.utils.response import success_response
import httpx
import os

router = APIRouter(
    prefix="/api/v1/risk",
    tags=["risk"]
)
EXECUTION_SERVICE_URL = os.getenv("EXECUTION_SERVICE_URL", "http://execution:8000")
STRATEGY_CORE_URL = os.getenv("STRATEGY_CORE_URL", "http://strategy-core:8000")

@router.post("/check", response_model=APIResponse[RiskCheckResponse])
async def check_risk(req: RiskCheckRequest):
    """
    Proxy risk check to the Strategy Core Service.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Forward request to strategy-core service
            response = await client.post(
                f"{STRATEGY_CORE_URL}/api/v1/risk/check", 
                json=req.model_dump(mode='json'),
                timeout=5.0
            )
            response.raise_for_status()
            return success_response(data=response.json())
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Execution service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Execution service error: {exc.response.text}")
