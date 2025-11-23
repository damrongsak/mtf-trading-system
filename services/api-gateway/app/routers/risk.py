from fastapi import APIRouter, HTTPException
from app.schemas.trade import RiskCheckRequest, RiskCheckResponse
import httpx
import os

router = APIRouter()
EXECUTION_SERVICE_URL = os.getenv("EXECUTION_SERVICE_URL", "http://execution:8000")

@router.post("/check", response_model=RiskCheckResponse)
async def check_risk(req: RiskCheckRequest):
    """
    Proxy risk check to the Execution Service.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Forward request to execution service
            # We assume the execution service accepts the same JSON structure
            response = await client.post(
                f"{EXECUTION_SERVICE_URL}/check", 
                json=req.model_dump(mode='json'),
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Execution service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Execution service error: {exc.response.text}")
