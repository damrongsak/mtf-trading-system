#!/usr/bin/env python3
"""
E2E Test Script: Soda → Olympus → Broker
=========================================
Low-risk LIMIT order test with ATR-based price guardrails.
"""
import asyncio
import json
import os
import time
from datetime import datetime

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://host.docker.internal:8000")
ACCOUNT_ID = "4438a19e-5d19-48c9-89d6-5134ee996591"
SYMBOL = "XAU_USD"
VOLUME = 0.01
ATR_PERIOD = 14
ATR_MULTIPLIER = 5
CLIENT_ORDER_ID = f"e2e_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


async def get_auth_token():
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GATEWAY_URL}/api/v1/auth/token",
            data={"username": "trader1", "password": "password123"}
        )
        if response.status_code == 200:
            return response.json()["auth"]["access_token"]
        raise Exception(f"Auth failed: {response.text}")


async def get_candles(token, symbol="XAUUSD"):
    import httpx
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GATEWAY_URL}/api/v1/market/candles",
            params={"symbol": symbol, "timeframe": "M5", "limit": 20},
            headers=headers, timeout=10.0
        )
        return resp.json()


def calculate_atr(candles):
    if len(candles) < 15:
        return 50.0
    trs = []
    for i in range(1, len(candles)):
        h = float(candles[i].get("h", candles[i].get("high", 0)))
        l = float(candles[i].get("l", candles[i].get("low", 0)))
        pc = float(candles[i-1].get("c", candles[i-1].get("close", 0)))
        tr = max(h-l, abs(h-pc), abs(l-pc))
        trs.append(tr)
    return sum(trs[-14:])/14 if len(trs) >= 14 else sum(trs)/len(trs)


def calc_safe_entry(price, atr, direction):
    off = atr * ATR_MULTIPLIER
    if direction == "BUY":
        entry = price - off
        sl = entry - atr * 2
        tp = entry + atr * 6
    else:
        entry = price + off
        sl = entry + atr * 2
        tp = entry - atr * 6
    return {"entry_price": round(entry, 2), "stop_loss": round(sl, 2), "take_profit": round(tp, 2)}


async def place_order(token, payload):
    import httpx
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        t0 = time.time()
        resp = await client.post(f"{GATEWAY_URL}/api/v1/execution/orders", json=payload, headers=headers, timeout=30.0)
        return {"status": resp.status_code, "latency_ms": round((time.time()-t0)*1000, 2), "body": resp.json() if resp.status_code < 400 else resp.text}


async def get_orders(token):
    import httpx
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GATEWAY_URL}/api/v1/execution/orders", headers=headers, timeout=10.0)
        return resp.json() if resp.status_code == 200 else []


async def main(dry_run=False):
    print("=" * 60)
    print("E2E Test: Soda → Olympus → Broker (LIMIT Order)")
    print("=" * 60)
    
    print("\n[1/4] Authenticating...")
    token = await get_auth_token()
    print(f"    Token: {token[:20]}...")
    
    print("\n[2/4] Fetching market data...")
    candles = await get_candles(token)
    price = float(candles[-1]["close"])
    atr = calculate_atr(candles)
    print(f"    Price: {price:.2f}, ATR: {atr:.2f}")
    
    print("\n[3/4] Calculating safe entry (BUY)...")
    safe = calc_safe_entry(price, atr, "BUY")
    print(f"    Entry: {safe['entry_price']:.2f}, SL: {safe['stop_loss']:.2f}, TP: {safe['take_profit']:.2f}")
    
    payload = {
        "broker_account_id": ACCOUNT_ID,
        "symbol": SYMBOL,
        "direction": "BUY",
        "volume": VOLUME,
        "order_type": "LIMIT",
        "entry_price": safe["entry_price"],
        "stop_loss": safe["stop_loss"],
        "take_profit": safe["take_profit"],
        "client_order_id": CLIENT_ORDER_ID,
        "comment": "E2E_TEST"
    }
    print(f"\n    Payload: {json.dumps(payload, indent=6)}")
    
    if dry_run:
        print("\n    DRY RUN - No order sent")
        return
    
    print("\n[4/4] Placing order...")
    result = await place_order(token, payload)
    print(f"    Status: {result['status']}, Latency: {result['latency_ms']}ms")
    print(f"    Response: {json.dumps(result['body'], indent=6)}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main(dry_run=("--dry-run" in __import__("sys").argv)))
