from fastapi import APIRouter, HTTPException, Body
from app.services.internal_client import execution_client
from typing import Dict, Any

router = APIRouter(
    prefix="/execution",
    tags=["execution"]
)

@router.get("/account/summary")
async def get_account_summary():
    try:
        data = await execution_client.get_account_summary()
        return data
    except Exception as e:
        # Improve error handling (e.g. 503 if services down)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orders")
async def place_order(order_data: Dict[str, Any]):
    try:
        data = await execution_client.place_order(order_data)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
