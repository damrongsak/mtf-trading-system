from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
import websockets
import asyncio
import os
import json
from app.security import SECRET_KEY, ALGORITHM
from jose import jwt, JWTError

router = APIRouter(tags=["stream"])



@router.websocket("/prices")
async def websocket_endpoint(websocket: WebSocket, symbols: str = "EUR_USD,XAU_USD", token: str = Query(...), source: str = Query(None)):
    # Authenticate
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except (JWTError, Exception):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Parse symbols
    requested_symbols = [s.strip() for s in symbols.split(",") if s.strip()]
    if not requested_symbols:
        await websocket.close(code=1000)
        return

    from app.streaming.manager import stream_manager
    
    # Register connection
    await stream_manager.connect(websocket, requested_symbols, source)
    
    try:
        while True:
            # Keep the connection open and listen for disconnects
            # We don't expect messages from client, but we need to await
            await websocket.receive_text()
    except WebSocketDisconnect:
        await stream_manager.disconnect(websocket, requested_symbols)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await stream_manager.disconnect(websocket, requested_symbols)

