from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
import websockets
import asyncio
import os
import json
from app.security import SECRET_KEY, ALGORITHM
from jose import jwt, JWTError

router = APIRouter(tags=["stream"])

STRATEGY_CORE_WS_URL = os.getenv("STRATEGY_CORE_WS_URL", "ws://strategy-core:8000/ws/prices")

@router.websocket("/prices")
async def websocket_endpoint(websocket: WebSocket, symbols: str = "EUR_USD,XAU_USD", token: str = Query(...)):
    # Authenticate
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    
    # Construct upstream URL with query params
    upstream_url = f"{STRATEGY_CORE_WS_URL}?symbols={symbols}"
    
    # Connect to Strategy Core
    try:
        async with websockets.connect(upstream_url) as service_ws:
            # Proxy loop
            try:
                while True:
                    # Receieve from upstream
                    msg = await service_ws.recv()
                    # Send to client
                    await websocket.send_text(msg)
            except WebSocketDisconnect:
                pass # Client disconnect is normal
            except Exception as e:
                print(f"Proxy loop error: {e}")
    except Exception as e:
        print(f"Failed to connect to Strategy Core: {e}")
        try:
            await websocket.close(code=1011)
        except:
            pass
