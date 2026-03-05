#!/usr/bin/env python3
"""
MTF Olympus - Core WebSocket Command Tests
Test Cases: A1 - A7

Usage:
    python scripts/ws_test_core.py
"""

import asyncio
import json
import time
import hashlib
import hmac
import os
from datetime import datetime
from pathlib import Path

try:
    import websockets
except ImportError:
    print("❌ websockets not installed. Run: pip install websockets")
    exit(1)

# ================= CONFIGURATION =================
# From MEMORY.md
BASE_URL = "ws://localhost:8000/api/v1/external/ws/command"
API_KEY = "test_api_key_123"
API_SECRET = "test_secret_456"
BROKER_ACCOUNT_ID = "4438a19e-5d19-48c9-89d6-5134ee996591"

# Safe test prices (far from market)
XAUUSD_PRICE = 5050.00  # Test price (market ~2900)
SL_OFFSET = 10.0
TP_OFFSET = 10.0
# =================================================

class WSClient:
    def __init__(self, url, api_key, api_secret):
        self.url = url
        self.api_key = api_key
        self.api_secret = api_secret
        self.ws = None
        self.authenticated = False
    
    async def connect(self):
        """Establish WebSocket connection"""
        self.ws = await websockets.connect(self.url)
        print(f"✅ Connected to {self.url}")
    
    def generate_signature(self, timestamp):
        """Generate HMAC-SHA256 signature"""
        message = f"{timestamp}GET/api/v1/external/ws/command"
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    async def authenticate(self):
        """Authenticate with API key"""
        timestamp = str(int(time.time()))
        signature = self.generate_signature(timestamp)
        
        auth_msg = {
            "cmd": "auth",
            "id": "auth_001",
            "params": {
                "api_key": self.api_key,
                "timestamp": timestamp,
                "signature": signature
            }
        }
        
        await self.ws.send(json.dumps(auth_msg))
        response = await self.ws.recv()
        data = json.loads(response)
        
        if data.get("status") == "success":
            self.authenticated = True
            print(f"✅ Authenticated: {data.get('message', 'OK')}")
            return True
        else:
            print(f"❌ Auth failed: {data}")
            return False
    
    async def send_command(self, cmd, params, cmd_id=None):
        """Send command and measure latency"""
        if cmd_id is None:
            cmd_id = f"{cmd}_{int(time.time() * 1000)}"
        
        message = {
            "cmd": cmd,
            "id": cmd_id,
            "params": params
        }
        
        start = time.perf_counter()
        await self.ws.send(json.dumps(message))
        response = await self.ws.recv()
        latency = (time.perf_counter() - start) * 1000
        
        return json.loads(response), latency
    
    async def close(self):
        """Close connection"""
        if self.ws:
            await self.ws.close()
            print("🔌 Connection closed")


async def test_a1_connect():
    """Test A1: WebSocket Connect + Auth"""
    print("\n" + "="*50)
    print("TEST A1: WebSocket Connect + Auth")
    print("="*50)
    
    client = WSClient(BASE_URL, API_KEY, API_SECRET)
    
    try:
        await client.connect()
        success = await client.authenticate()
        
        if success:
            print(f"✅ A1 PASSED")
            return True, client
        else:
            print(f"❌ A1 FAILED")
            return False, None
    except Exception as e:
        print(f"❌ A1 ERROR: {e}")
        return False, None


async def test_a2_get_account(client):
    """Test A2: Get Account Summary"""
    print("\n" + "="*50)
    print("TEST A2: Get Account Summary")
    print("="*50)
    
    params = {"broker_account_id": BROKER_ACCOUNT_ID}
    response, latency = await client.send_command("get_account", params)
    
    print(f"Response: {json.dumps(response, indent=2)}")
    print(f"Latency: {latency:.1f}ms")
    
    if response.get("status") == "success":
        balance = response.get("data", {}).get("balance", 0)
        print(f"✅ A2 PASSED - Balance: ${balance}")
        return True
    else:
        print(f"❌ A2 FAILED")
        return False


async def test_a3_get_orders(client):
    """Test A3: Get Open Orders"""
    print("\n" + "="*50)
    print("TEST A3: Get Open Orders")
    print("="*50)
    
    params = {"broker_account_id": BROKER_ACCOUNT_ID}
    response, latency = await client.send_command("get_orders", params)
    
    print(f"Response: {json.dumps(response, indent=2)}")
    print(f"Latency: {latency:.1f}ms")
    
    if response.get("status") == "success":
        print(f"✅ A3 PASSED")
        return True
    else:
        print(f"❌ A3 FAILED")
        return False


async def test_a4_execute_order(client, symbol="XAUUSD", direction="BUY"):
    """Test A4: Execute LIMIT Order"""
    print("\n" + "="*50)
    print(f"TEST A4: Execute LIMIT Order ({direction} {symbol})")
    print("="*50)
    
    params = {
        "broker_account_id": BROKER_ACCOUNT_ID,
        "symbol": symbol,
        "direction": direction,
        "order_type": "LIMIT",
        "units": 0.01,
        "price": XAUUSD_PRICE,
        "sl_price": XAUUSD_PRICE - SL_OFFSET,
        "tp_price": XAUUSD_PRICE + TP_OFFSET
    }
    
    response, latency = await client.send_command("execute", params)
    
    print(f"Response: {json.dumps(response, indent=2)}")
    print(f"Latency: {latency:.1f}ms")
    
    if response.get("status") == "success":
        order_id = response.get("data", {}).get("id")
        print(f"✅ A4 PASSED - Order ID: {order_id}")
        return True, order_id
    else:
        print(f"❌ A4 FAILED: {response.get('error', 'Unknown')}")
        return False, None


async def test_a5_cancel_order(client, order_id):
    """Test A5: Cancel Order"""
    print("\n" + "="*50)
    print(f"TEST A5: Cancel Order {order_id}")
    print("="*50)
    
    params = {
        "broker_account_id": BROKER_ACCOUNT_ID,
        "order_id": order_id
    }
    
    response, latency = await client.send_command("cancel", params)
    
    print(f"Response: {json.dumps(response, indent=2)}")
    print(f"Latency: {latency:.1f}ms")
    
    if response.get("status") == "success":
        print(f"✅ A5 PASSED")
        return True
    else:
        print(f"❌ A5 FAILED")
        return False


async def test_a6_amend_order(client, order_id, new_sl=None, new_tp=None):
    """Test A6: Amend Order (SL/TP)"""
    print("\n" + "="*50)
    print(f"TEST A6: Amend Order {order_id}")
    print("="*50)
    
    params = {
        "broker_account_id": BROKER_ACCOUNT_ID,
        "order_id": order_id
    }
    
    if new_sl:
        params["sl_price"] = new_sl
    if new_tp:
        params["tp_price"] = new_tp
    
    response, latency = await client.send_command("amend", params)
    
    print(f"Response: {json.dumps(response, indent=2)}")
    print(f"Latency: {latency:.1f}ms")
    
    if response.get("status") == "success":
        print(f"✅ A6 PASSED")
        return True
    else:
        print(f"❌ A6 FAILED: {response.get('error', 'Unknown')}")
        return False


async def test_a7_close_position(client, trade_id, units=0.01):
    """Test A7: Close Position"""
    print("\n" + "="*50)
    print(f"TEST A7: Close Position {trade_id}")
    print("="*50)
    
    params = {
        "broker_account_id": BROKER_ACCOUNT_ID,
        "trade_id": trade_id,
        "units": units
    }
    
    response, latency = await client.send_command("close", params)
    
    print(f"Response: {json.dumps(response, indent=2)}")
    print(f"Latency: {latency:.1f}ms")
    
    if response.get("status") == "success":
        print(f"✅ A7 PASSED")
        return True
    else:
        print(f"❌ A7 FAILED: {response.get('error', 'Unknown')}")
        return False


async def run_all_tests():
    """Run all core tests"""
    print("🚀 MTF Olympus - Core WebSocket Tests")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Broker: {BROKER_ACCOUNT_ID}")
    
    results = {}
    
    # A1: Connect + Auth
    success, client = await test_a1_connect()
    results["A1"] = success
    
    if not client:
        print("\n❌ Cannot proceed - auth failed")
        return results
    
    # A2: Get Account
    results["A2"] = await test_a2_get_account(client)
    
    # A3: Get Orders
    results["A3"] = await test_a3_get_orders(client)
    
    # A4: Execute Order
    success, order_id = await test_a4_execute_order(client)
    results["A4"] = success
    
    # A5: Cancel Order (if we have order_id)
    if order_id:
        results["A5"] = await test_a5_cancel_order(client, order_id)
    
    # A6: Amend Order (needs pending order)
    # Note: Skip for now - need pending order
    print("\n" + "="*50)
    print("TEST A6: Amend Order - SKIPPED (requires pending order)")
    print("="*50)
    results["A6"] = None
    
    # A7: Close Position (needs open position)
    # Note: Skip for now - need open position
    print("\n" + "="*50)
    print("TEST A7: Close Position - SKIPPED (requires open position)")
    print("="*50)
    results["A7"] = None
    
    # Close connection
    await client.close()
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    for test, result in results.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⏭️  SKIP"
        print(f"{test}: {status}")
    
    passed = sum(1 for r in results.values() if r is True)
    total = len([r for r in results.values() if r is not None])
    print(f"\nTotal: {passed}/{total} passed")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_all_tests())
