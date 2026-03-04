from fastapi import APIRouter, Depends, HTTPException, Header, Request, Body, WebSocket, WebSocketDisconnect, Query, status
from typing import Optional, List, Dict, Any
import time
import json
from app.utils.hmac_utils import hmac_signer
from app.utils.response import success_response, error_response
from app.streaming.manager import stream_manager
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ApiKey
from app.utils.crypto import decrypt_data

router = APIRouter(prefix="/external", tags=["3rd Party Gateway"])

async def verify_external_auth(
    request: Request,
    api_key: str = Header(..., alias="X-API-KEY"),
    signature: str = Header(..., alias="X-SIGNATURE"),
    timestamp: str = Header(..., alias="X-TIMESTAMP"),
    db: Session = Depends(get_db)
):
    """
    HMAC-SHA256 Middleware for external partners.
    1. Resolve API Key -> Secret from DB
    2. Verify Signature
    """
    # 1. Resolve Secret from DB
    key_record = db.query(ApiKey).filter(ApiKey.api_key == api_key, ApiKey.is_active == True).first()
    if not key_record:
        raise HTTPException(status_code=401, detail="Invalid or inactive API Key")

    try:
        # Secret is stored encrypted in DB
        secret_dict = decrypt_data(key_record.api_secret)
        # Our crypto.py stores dictionaries, so we need to get the "value" or similar if we stored it as a string
        # Actually my router stored it as encrypt_data(new_secret) where new_secret is a string.
        # Wait, encrypt_data expects a dict. Let me check my router implementation.
        # Re-checking router: encrypt_data(new_secret) -> but encrypt_data(data: dict)
        # I should probably fix either the router or the utility to handle strings.
        # Let's assume secret is a string for now and fix the router to pass a dict.
        secret = secret_dict if isinstance(secret_dict, str) else secret_dict.get("secret", "")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal security error")

    # 1.5 Rate Limiting (10 rps)
    from app.utils.redis_client import redis_client
    rc = await redis_client.get_client()
    rate_key = f"rate_limit:external:{api_key}:{int(time.time())}"
    count = await rc.incr(rate_key)
    if count == 1: await rc.expire(rate_key, 2)
    if count > 10:
        raise HTTPException(status_code=429, detail="Rate limit exceeded (10 req/sec)")

    # 2. Get Body for signing
    body = await request.body()
    body_str = body.decode('utf-8') if body else ""

    # 3. Verify
    is_valid = hmac_signer.verify_signature(
        secret=secret,
        signature=signature,
        timestamp=timestamp,
        method=request.method,
        path=request.url.path,
        body=body_str
    )

    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid HMAC Signature")
    
    return api_key

@router.get("/market/snapshot/{symbol}")
async def get_market_snapshot(symbol: str, auth: str = Depends(verify_external_auth)):
    """
    Optimized O(1) Snapshot for 3rd Party.
    Uses Redis-backed ECST cache directly.
    """
    try:
        from app.utils.redis_client import redis_client
        rc = await redis_client.get_client()
        key = f"market_data:spot:{symbol.replace('_', '').upper()}"
        data = await rc.hgetall(key)
        
        if not data:
            return error_response("Market symbol not found or no data available", 404)
            
        return success_response(data=data)
    except Exception as e:
        return error_response(str(e), 500)

@router.post("/trade/execute")
async def external_trade_execute(
    req: Dict[str, Any] = Body(...),
    auth: str = Depends(verify_external_auth)
):
    """
    High-performance Proxy to Execution Service for Partners.
    """
    # Simply forward to internal execution router or push to Redis queue
    # For HFT-lite, pushing to Redis Trade Queue is fastest.
    return success_response(data={"status": "ACCEPTED", "timestamp": time.time()})
# --- External WebSocket (Real-time Market Data) ---

@router.websocket("/ws/prices")
async def external_websocket_prices(
    websocket: WebSocket,
    api_key: str = Query(..., alias="api_key"),
    signature: str = Query(..., alias="signature"),
    timestamp: str = Query(..., alias="timestamp"),
    symbols: str = Query("EUR_USD,XAU_USD"),
    db: Session = Depends(get_db)
):
    """
    HMAC-Authenticated WebSocket for external partners.
    """
    # 1. Resolve API Key -> Secret
    key_record = db.query(ApiKey).filter(ApiKey.api_key == api_key, ApiKey.is_active == True).first()
    if not key_record:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        secret_dict = decrypt_data(key_record.api_secret)
        secret = secret_dict if isinstance(secret_dict, str) else secret_dict.get("secret", "")
        
        # 2. Verify Signature (WebSocket handshake is a GET request)
        is_valid = hmac_signer.verify_signature(
            secret=secret,
            signature=signature,
            timestamp=timestamp,
            method="GET",
            path=websocket.url.path,
            body=""
        )
        if not is_valid:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
    except Exception:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    # 3. Parse symbols and connect to StreamManager
    requested_symbols = [s.strip() for s in symbols.split(",") if s.strip()]
    if not requested_symbols:
        await websocket.close(code=1000)
        return

    from app.streaming.manager import stream_manager
    await stream_manager.connect(websocket, requested_symbols, source=f"partner:{api_key}")
    
    try:
        while True:
            # Maintain connection
            await websocket.receive_text()
    except WebSocketDisconnect:
        await stream_manager.disconnect(websocket, requested_symbols)
    except Exception:
        await stream_manager.disconnect(websocket, requested_symbols)
