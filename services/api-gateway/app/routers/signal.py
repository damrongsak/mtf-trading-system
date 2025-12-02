from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from app.schemas.signal import SignalResponse, SignalDirection
from app.schemas.response import APIResponse
from app.utils.response import success_response

router = APIRouter(
    prefix="/api/v1/signal",
    tags=["signal"],
    responses={404: {"description": "Not found"}},
)

@router.get("/latest/{symbol}", response_model=APIResponse[SignalResponse])
async def get_latest_signal(symbol: str):
    """
    Get the latest signal for a specific symbol.
    Currently returns a mock response until Strategy Core is integrated.
    """
    # Mock response for MVP verification
    data = SignalResponse(
        symbol=symbol.upper(),
        timeframe="15m",
        timestamp=datetime.utcnow(),
        direction=SignalDirection.LONG,
        entry_price=2000.00,
        sl_price=1990.00,
        tp_price=2020.00,
        reason="Mock signal for testing"
    )
    return success_response(data=data)

@router.post("/check", response_model=APIResponse[SignalResponse])
async def check_signal(symbol: str):
    """
    Trigger a manual signal check.
    """
    # Mock response
    data = SignalResponse(
        symbol=symbol.upper(),
        timeframe="15m",
        timestamp=datetime.utcnow(),
        direction=SignalDirection.SHORT,
        entry_price=2050.00,
        sl_price=2060.00,
        tp_price=2030.00,
        reason="Manual check triggered"
    )
    return success_response(data=data)
