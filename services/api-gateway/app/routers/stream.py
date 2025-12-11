from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import websockets
import asyncio
import os
import json

router = APIRouter(tags=["stream"])

STRATEGY_CORE_WS_URL = os.getenv("STRATEGY_CORE_WS_URL", "ws://strategy-core:8000/ws/prices")

@router.websocket("/prices")
async def websocket_endpoint(websocket: WebSocket, symbols: str = "EUR_USD,XAU_USD"):
    await websocket.accept()
    
    # Construct upstream URL with query params
    upstream_url = f"{STRATEGY_CORE_WS_URL}?symbols={symbols}"
    
    # Connect to Strategy Core
    try:
        async with websockets.connect(upstream_url) as service_ws:
            # Proxy loop
            # ... (rest is same, but let's be concise in replacement)
            try:
                while True:
                    msg = await service_ws.recv()
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
