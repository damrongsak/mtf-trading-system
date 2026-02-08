from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
from app.schemas.signal import SignalResponse, SignalDirection
from app.models.signal_log import SignalLog
from app.database import get_db
from sqlalchemy.orm import Session
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

@router.get("/detected", response_model=APIResponse[List[SignalResponse]])
async def get_detected_signals(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get signals that were detected and persisted in the database.
    (Includes both executed and non-executed signals from deployments)
    """
    logs = db.query(SignalLog).order_by(SignalLog.timestamp.desc()).limit(limit).all()
    
    results = []
    for log in logs:
        meta = log.meta_data or {}
        
        # Map DB model to Schema
        # Handle direction string to Enum
        try:
            direction = SignalDirection(log.direction)
        except:
            direction = SignalDirection.NEUTRAL

        results.append(SignalResponse(
            symbol=log.symbol,
            timeframe=log.timeframe or "H1",
            timestamp=log.timestamp,
            direction=direction,
            entry_price=log.price or 0.0,
            sl_price=meta.get("stop_loss") or 0.0,
            tp_price=meta.get("take_profit") or 0.0, # Might be missing in meta
            reason=log.reason,
            confidence=log.confidence or 0.0,
            strategy_name=log.strategy_name
        ))
        
    return success_response(data=results)

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
        try:
            # 1. Fetch Candles
            # We do NOT specify broker, letting data-pipeline pick the ACTIVE one (e.g. CTRADER).
            # This follows the project rule: "check active flag is true".
            
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
                    symbol=symbol.upper(), timeframe=timeframe, timestamp=datetime.now(timezone.utc),
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
                "symbol": symbol.upper(),
                "open": opens, 
                "high": highs, 
                "low": lows, 
                "close": closes, 
                "volume": volumes,
                "timestamps": [c["timestamp"] for c in candles_data]
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

    # 3. Use Strategic Results from Strategy Core
    direction = analysis.get("institutional_bias", "NEUTRAL")
    reason = analysis.get("strategic_reasoning", "No clear signal")
    
    # Map to Enum
    direction_enum = SignalDirection.NEUTRAL
    if direction == "BULLISH":
        direction_enum = SignalDirection.LONG
    elif direction == "BEARISH":
        direction_enum = SignalDirection.SHORT

    # 4. Calculate Market Status and Data Freshness
    from app.services.market_status import MarketStatusService
    
    market_service = MarketStatusService()
    status = await market_service.get_market_status(symbol)
    
    # Calculate data age
    from datetime import timezone
    now = datetime.now(timezone.utc)
    if isinstance(last_time, str):
        last_candle_time = datetime.fromisoformat(last_time.replace('Z', '+00:00'))
    else:
        last_candle_time = last_time
    
    age_seconds = int((now - last_candle_time).total_seconds())
    
    # Classify freshness
    if age_seconds < 300:  # < 5 minutes
        freshness = "real-time"
    elif age_seconds < 3600:  # < 1 hour
        freshness = "recent"
    else:
        freshness = "stale"

    return success_response(data=SignalResponse(
        symbol=symbol.upper(),
        timeframe=timeframe,
        timestamp=last_time,
        direction=direction_enum,
        entry_price=last_close,
        sl_price=last_close * 0.99 if direction_enum == SignalDirection.LONG else last_close * 1.01,
        tp_price=last_close * 1.02 if direction_enum == SignalDirection.LONG else last_close * 0.98,
        reason=reason,
        analysis=analysis,
        strategy_name="Smart Money Concepts (Scanner)",
        # Market context
        market_status="open" if status["is_open"] else "closed",
        market_reason=status["reason"],
        data_age_seconds=age_seconds,
        data_freshness=freshness
    ))

@router.post("/check", response_model=APIResponse[SignalResponse])
async def check_signal(symbol: str):
    """
    Trigger a manual signal check.
    Delegates to get_latest_signal logic.
    """
    return await get_latest_signal(symbol)

from app.schemas.signal import SignalBatchRequest

@router.post("/batch", response_model=APIResponse[List[SignalResponse]])
async def get_batch_signals(req: SignalBatchRequest):
    """
    Batch fetch and analyze signals for all active symbols of a broker.
    Optimization:
    1. Fetch symbol list from Data Pipeline
    2. Fetch candles for all symbols (Parallel)
    3. Batch Analyze in Strategy Core
    """
    async with httpx.AsyncClient() as client:
        # 1. Fetch active symbols
        try:
            symbols_resp = await client.get(
                f"{DATA_SERVICE_URL}/api/v1/symbols",
                params={"broker": req.broker},
                timeout=5.0
            )
            symbols_resp.raise_for_status()
            symbols = symbols_resp.json()
        except Exception as e:
            return success_response(data=[])
            
        if not symbols:
            return success_response(data=[])
            
        # 2. Fetch candles in parallel
        # We limit specific timeframe to 'H1' for now as per system default
        timeframe = "H1"
        
        async def fetch_candle(sym):
            try:
                # Use default fallback behavior? No, we filter by broker so we should find it.
                # Just call get_candles proxy we made in data.py? No, call direct data-pipeline
                resp = await client.get(
                    f"{DATA_SERVICE_URL}/api/v1/candles",
                    params={"symbol": sym, "timeframe": timeframe, "page_size": 100, "broker": req.broker},
                    timeout=5.0
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    if data:
                        # Reverse needed? Data Pipeline usually returns DESC.
                        # Implementation check: yes it does order_by(desc)
                        data.reverse()
                        return sym, data
            except:
                pass
            return sym, []

        # Batch fetches
        tasks = [fetch_candle(sym) for sym in symbols]
        results = await asyncio.gather(*tasks)
        
        # Prepare payload for Strategy Core
        # SMCBatchRequest: { requests: { symbol: { open, high... } } }
        smc_requests = {}
        candle_map = {} # Store last candle info for response
        
        for sym, candles in results:
            if not candles or len(candles) < 10:
                continue
                
            opens = [float(c["open"]) for c in candles]
            highs = [float(c["high"]) for c in candles]
            lows = [float(c["low"]) for c in candles]
            closes = [float(c["close"]) for c in candles]
            volumes = [float(c["volume"]) for c in candles]
            
            smc_requests[sym] = {
                "open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes
            }
            candle_map[sym] = candles[-1] # Last candle for price info
            
        if not smc_requests:
             return success_response(data=[])

        # 3. Batch Analyze
        try:
            smc_resp = await client.post(
                f"{STRATEGY_SERVICE_URL}/api/v1/calculate/smc/batch",
                json={"requests": smc_requests},
                timeout=60.0 # Increased timeout for batch
            )
            smc_resp.raise_for_status()
            analysis_results = smc_resp.json().get("results", {})
        except Exception as e:
             import logging
             logging.getLogger("uvicorn.error").error(f"Strategy Core Batch Error: {str(e)}")
             raise HTTPException(status_code=503, detail=f"Strategy Core Batch Error: {str(e)}")
             
        # 4. Process Results
        final_response = []
        
        for sym, analysis in analysis_results.items():
            last_candle = candle_map.get(sym)
            if not last_candle: 
                continue
                
            last_close = float(last_candle["close"])
            last_time = last_candle["timestamp"]
            
            # 4. Use Strategic Results from Strategy Core
            direction = analysis.get("institutional_bias", "NEUTRAL")
            reason = analysis.get("strategic_reasoning", "No clear signal")
            
            # Map to Enum
            direction_enum = SignalDirection.NEUTRAL
            if direction == "BULLISH":
                direction_enum = SignalDirection.LONG
            elif direction == "BEARISH":
                direction_enum = SignalDirection.SHORT
            
            # Calculate SL/TP
            sl = last_close * 0.99 if direction_enum == SignalDirection.LONG else last_close * 1.01
            tp = last_close * 1.02 if direction_enum == SignalDirection.LONG else last_close * 0.98
            
            final_response.append(SignalResponse(
                symbol=sym,
                timeframe=timeframe,
                timestamp=last_time,
                direction=direction_enum,
                entry_price=last_close,
                sl_price=sl,
                tp_price=tp,
                reason=reason,
                broker=req.broker,
                strategy_name="Smart Money Concepts (Scanner)"
            ))
            
        return success_response(data=final_response)

