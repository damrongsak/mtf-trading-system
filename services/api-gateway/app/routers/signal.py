from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
from app.schemas.signal import SignalResponse, SignalDirection
from app.schemas.response import APIResponse
from app.utils.response import success_response
import httpx
import os
import asyncio

router = APIRouter(
    prefix="/api/v1/signal",
    tags=["signal"],
    responses={404: {"description": "Not found"}},
)

DATA_SERVICE_URL = os.getenv("DATA_PIPELINE_URL", "http://data-pipeline:8000")
STRATEGY_SERVICE_URL = os.getenv("STRATEGY_CORE_URL", "http://strategy-core:8000")

@router.get("/latest/{symbol:path}", response_model=APIResponse[SignalResponse])
async def get_latest_signal(symbol: str, timeframe: str = "H1"):
    """
    Get the latest signal for a specific symbol by orchestrating:
    1. Fetch candles from Data Pipeline
    2. Analyze using Strategy Core (SMC)
    3. Determine Signal
    """
    async with httpx.AsyncClient() as client:
        # 1. Fetch Candles
        try:
            # Note: timeframe format mismatch might occur (H1 vs 1h). 
            # Assuming data-pipeline uses standard formats like 'H1'.
            candles_resp = await client.get(
                f"{DATA_SERVICE_URL}/api/v1/candles",
                params={"symbol": symbol.upper(), "timeframe": timeframe, "page_size": 100},
                timeout=10.0
            )
            candles_resp.raise_for_status()
            candles_data = candles_resp.json().get("data", [])
            
            if not candles_data:
                 # Fallback/Empty
                return success_response(data=SignalResponse(
                    symbol=symbol.upper(), timeframe=timeframe, timestamp=datetime.utcnow(),
                    direction=SignalDirection.NEUTRAL, entry_price=0, sl_price=0, tp_price=0,
                    reason="No data available"
                ))
            
            # Sort candles by timestamp ascending for analysis (API returns desc usually)
            # Check implementation of data-pipeline: order_by(Candle.timestamp.desc())
            # So we need to reverse them.
            candles_data.reverse()
            
            opens = [float(c["open"]) for c in candles_data]
            highs = [float(c["high"]) for c in candles_data]
            lows = [float(c["low"]) for c in candles_data]
            closes = [float(c["close"]) for c in candles_data]
            volumes = [float(c["volume"]) for c in candles_data]
            last_close = closes[-1]
            last_time = candles_data[-1]["timestamp"]

        except Exception as e:
             raise HTTPException(status_code=503, detail=f"Data Service Error: {str(e)}")

        # 2. Analyze with Strategy Core
        try:
            smc_payload = {
                "open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes
            }
            smc_resp = await client.post(
                f"{STRATEGY_SERVICE_URL}/api/v1/calculate/smc",
                json=smc_payload,
                timeout=10.0
            )
            smc_resp.raise_for_status()
            analysis = smc_resp.json()
            
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Strategy Service Error: {str(e)}")

    # 3. Interpret Results (Simple Logic for MVP)
    # Check if price is inside an unmitigated Order Block
    direction = SignalDirection.NEUTRAL
    reason = "No clear signal"
    
    order_blocks = analysis.get("order_blocks", [])
    
    # Sort OBs by index (recent first)
    # They are likely returned in order of detection found
    
    for ob in reversed(order_blocks): # Check most recent OBs first
        if ob["mitigated"]:
            continue
            
        # Bullish OB (Support)
        if ob["type"] == "bullish":
            # If price is near or inside OB
            if ob["bottom"] <= last_close <= ob["top"] * 1.001: # 0.1% tolerance above
                direction = SignalDirection.LONG
                reason = f"Price reacting to Bullish OB at {ob['top']}"
                break
                
        # Bearish OB (Resistance)
        elif ob["type"] == "bearish":
            # If price is near or inside OB
            if ob["bottom"] * 0.999 <= last_close <= ob["top"]:
                direction = SignalDirection.SHORT
                reason = f"Price reacting to Bearish OB at {ob['bottom']}"
                break

    return success_response(data=SignalResponse(
        symbol=symbol.upper(),
        timeframe=timeframe,
        timestamp=last_time,
        direction=direction,
        entry_price=last_close,
        sl_price=last_close * 0.99 if direction == SignalDirection.LONG else last_close * 1.01,
        tp_price=last_close * 1.02 if direction == SignalDirection.LONG else last_close * 0.98,
        reason=reason
    ))

@router.post("/check", response_model=APIResponse[SignalResponse])
async def check_signal(symbol: str):
    """
    Trigger a manual signal check.
    Delegates to get_latest_signal logic.
    """
    return await get_latest_signal(symbol)
