from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
import websockets
import asyncio
import os
import json
from app.security import SECRET_KEY, ALGORITHM
from jose import jwt, JWTError

router = APIRouter(tags=["stream"])

from app.utils.redis_subscriber import RedisSubscriber

@router.websocket("/prices")
async def websocket_endpoint(websocket: WebSocket, symbols: str = "EUR_USD,XAU_USD", token: str = Query(...)):
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

    await websocket.accept()
    
    # Parse symbols and map to Redis channels
    # Channel format: market_data:EUR_USD
    requested_symbols = [s.strip() for s in symbols.split(",") if s.strip()]
    channels = [f"market_data:{s.replace('/', '_')}" for s in requested_symbols]
    
    if not channels:
        # If no symbols, just keep connection open? Or maybe subscribe to all? 
        # For now, close if empty request
        await websocket.close(code=1000)
        return

    subscriber = RedisSubscriber()
    
    try:
        await subscriber.connect()
        await subscriber.subscribe(channels)
        
        async for msg in subscriber.listen():
            if msg["type"] == "message":
                # Forward the raw JSON data from Redis to the WebSocket
                # Redis message data is string
                await websocket.send_text(msg["data"])
                
    except WebSocketDisconnect:
        pass # Client disconnected
    except Exception as e:
        print(f"Stream error: {e}")
        try:
            await websocket.close(code=1011)
        except:
            pass
    finally:
        await subscriber.close()
