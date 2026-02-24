import os
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.utils.response import success_response
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["quant"]
)

STRATEGY_CORE_URL = os.getenv("STRATEGY_CORE_URL", "http://strategy-core:8000")
http_client = httpx.AsyncClient(timeout=60.0)

@router.on_event("startup")
async def startup_event():
    global http_client
    http_client = httpx.AsyncClient(timeout=60.0)

@router.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()

class QuantAnalyzeRequest(BaseModel):
    symbol: str
    timeframe: str = "H1"
    limit: int = 1000

class QuantSizingRequest(BaseModel):
    symbol: str
    entry_price: float
    stop_loss: float
    equity: float
    strategy_id: Optional[str] = None
    timeframe: str = "H1"
    limit: int = 1000

@router.post("/analyze", status_code=200)
async def proxy_quant_analyze(req: QuantAnalyzeRequest):
    """
    Proxy Quant Map analysis to Strategy Core.
    """
    try:
        response = await http_client.post(
            f"{STRATEGY_CORE_URL}/api/v1/quant/analyze",
            json=req.model_dump()
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return success_response(data=response.json().get("data") if response.json().get("data") else response.json())
    except httpx.RequestError as e:
        logger.error(f"Strategy Core unavailable: {str(e)}")
        raise HTTPException(status_code=503, detail="Strategy Core unavailable")
    except Exception as e:
        logger.error(f"Quant Analyze Proxy failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/size", status_code=200)
async def proxy_quant_sizing(req: QuantSizingRequest):
    """
    Proxy Quant Positioning/Sizing to Strategy Core.
    """
    try:
        response = await http_client.post(
            f"{STRATEGY_CORE_URL}/api/v1/quant/size",
            json=req.model_dump()
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return success_response(data=response.json().get("data") if response.json().get("data") else response.json())
    except httpx.RequestError as e:
        logger.error(f"Strategy Core unavailable: {str(e)}")
        raise HTTPException(status_code=503, detail="Strategy Core unavailable")
    except Exception as e:
        logger.error(f"Quant Sizing Proxy failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
