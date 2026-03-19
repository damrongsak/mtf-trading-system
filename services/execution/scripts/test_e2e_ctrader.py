import asyncio
import os
import uuid
import sys
import httpx
import websockets
import json

class Fore:
    GREEN = '\033[92m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
class Style:
    RESET_ALL = '\033[0m'

# The API Gateway is usually exposed on port 8000.
API_BASE_URL = os.getenv("API_GATEWAY_URL", "http://api-gateway:8000/api/v1")
WS_BASE_URL = os.getenv("WS_GATEWAY_URL", "ws://api-gateway:8000/api/v1/stream/prices")

USERNAME = "trader1"
PASSWORD = "password123"
SYMBOL = "EURUSD"
SYMBOL_RAW = "EURUSD"
SOURCE = "CTRADER"
LOTS = 0.01

print("Using API Base URL:", API_BASE_URL)

class State:
    token = None
    account_id = None
    market_trade_id = None
    limit_order_id = None
    current_ask = 0.0
    current_bid = 0.0

state = State()

def log_test(step: str, result: bool, details: str = ""):
    status_color = Fore.GREEN if result else Fore.RED
    status_icon = "✅" if result else "❌"
    print(f"{status_color}{status_icon} [{step}] {details}{Style.RESET_ALL}")
    if not result:
        print(f"{Fore.YELLOW}Aborting subsequent E2E tests due to failure.{Style.RESET_ALL}")
        sys.exit(1)

def get_headers():
    return {
        "Authorization": f"Bearer {state.token}",
        "Content-Type": "application/json"
    }

async def authenticate():
    print(f"\n{Fore.CYAN}--- P0: Authentication ---{Style.RESET_ALL}")
    async with httpx.AsyncClient() as client:
        data = {"username": USERNAME, "password": PASSWORD}
        res = await client.post(f"{API_BASE_URL}/auth/token", data=data)
        
        if res.status_code == 200:
            resp_data = res.json()
            state.token = resp_data.get("auth", {}).get("access_token")
            if state.token:
                log_test("Auth", True, "Successfully acquired JWT token.")
            else:
                log_test("Auth", False, "Token missing in response.")
        else:
            log_test("Auth", False, f"HTTP {res.status_code}: {res.text}")

async def get_account():
    print(f"\n{Fore.CYAN}--- P1: Internal Account Fetch ---{Style.RESET_ALL}")
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{API_BASE_URL}/execution/accounts", headers=get_headers())
        if res.status_code == 200:
            accounts = res.json().get("data", [])
            ctrader_acc = next((a for a in accounts if a["broker_name"] == "CTRADER"), None)
            if ctrader_acc:
                state.account_id = ctrader_acc["id"]
                log_test("Account", True, f"Found CTRADER Account ID: {state.account_id}")
            else:
                log_test("Account", False, "No CTRADER account found for trader1.")
        else:
            log_test("Account", False, f"HTTP {res.status_code}: {res.text}")

async def test_websocket():
    print(f"\n{Fore.CYAN}--- P2: WebSocket Streaming & Pricing ---{Style.RESET_ALL}")
    try:
        ws_url = f"{WS_BASE_URL}?token={state.token}&symbols={SYMBOL_RAW}&source={SOURCE}"
        async with websockets.connect(ws_url) as ws:
            log_test("WS Connection", True, "Successfully connected and authenticated via Query Params.")
            
            tick_msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
            if isinstance(tick_msg, bytes):
                tick_msg = tick_msg.decode('utf-8')
            
            data = json.loads(tick_msg)
            msg_type = data.get("type", "").upper()
            instrument = data.get("instrument", data.get("symbol", ""))
            
            if msg_type == "PRICE" and instrument.replace("/", "") == SYMBOL:
                state.current_ask = float(data.get("ask", 1.10000))
                state.current_bid = float(data.get("bid", 1.10000))
                log_test("WS Tick", True, f"Received Tick - Bid: {state.current_bid} Ask: {state.current_ask}")
            else:
                log_test("WS Tick", False, f"Unexpected msg format: {tick_msg}")
    except Exception as e:
        log_test("WS Tick", False, f"WebSocket Error: {e}")
        # Fallback price for testing purposes if stream is not up
        state.current_ask = 1.10000
        state.current_bid = 1.09990
        print(f"{Fore.YELLOW}⚠️ Using fallback price 1.10000 for testing.{Style.RESET_ALL}")

async def inspect_trade(trade_id: str):
    print(f"{Fore.CYAN}--- Inspecting Trade {trade_id} (Human-like Verification) ---{Style.RESET_ALL}")
    async with httpx.AsyncClient() as client:
        print(f"{Fore.YELLOW}⏳ Sleeping 10s to simulate human reaction time...{Style.RESET_ALL}")
        await asyncio.sleep(10)
        
        res = await client.get(f"{API_BASE_URL}/execution/trades", params={"broker_account_id": state.account_id}, headers=get_headers())
        if res.status_code == 200:
            trades = res.json().get("data", [])
            trade = next((t for t in trades if str(t.get("id")) == str(trade_id) or str(t.get("broker_trade_id")) == str(trade_id)), None)
            if trade:
                sl = trade.get("sl_price")
                tp = trade.get("tp_price")
                log_test(f"Inspect Trade {trade_id}", True, f"Broker Verified -> SL: {sl}, TP: {tp}")
                print(f"{Fore.GREEN}👉 VISUAL CHECK: Log in to cTrader and look for Trade. SL/TP should be visible.{Style.RESET_ALL}")
            else:
                log_test(f"Inspect Trade {trade_id}", False, "Trade not found in sync list.")
        else:
            log_test(f"Inspect Trade {trade_id}", False, f"HTTP {res.status_code}: {res.text}")

async def test_market_order():
    print(f"\n{Fore.CYAN}--- P4: REST MARKET Order + SL/TP (Human-like) ---{Style.RESET_ALL}")
    
    await test_websocket()
    if state.current_ask == 0.0:
        state.current_ask = 1.10000
    
    sl_price = round(state.current_ask - 0.0050, 5) # EURUSD 50 pips
    tp_price = round(state.current_ask + 0.0050, 5)
    
    payload = {
        "broker_account_id": state.account_id,
        "trade_id": str(uuid.uuid4()),
        "symbol": SYMBOL_RAW,
        "order_type": "MARKET",
        "units": float(LOTS * 100000), # Standardize to 1000 units (micro lot)
        "sl_price": float(sl_price),
        "tp_price": float(tp_price)
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(f"{API_BASE_URL}/execution/orders", json=payload, headers=get_headers())
        if res.status_code == 200:
            data = res.json().get("data", {})
            if "id" in data:
                # For cTrader, use position_id for amending/closing OPEN positions
                state.market_trade_id = data.get("position_id", data["id"])
                log_test("MARKET Order", True, f"Trade opened. Order ID: {data['id']}, Position ID: {state.market_trade_id}")
                await inspect_trade(state.market_trade_id)
            else:
                log_test("MARKET Order", False, f"Invalid response: {data}")
        else:
             log_test("MARKET Order", False, f"HTTP {res.status_code}: {res.text}")

async def test_amend_position():
    print(f"\n{Fore.CYAN}--- P5: REST Amend TP (Open Position) ---{Style.RESET_ALL}")
    
    new_tp = round(state.current_ask + 0.0070, 5) # 70 pips above
    payload = {
        "broker_account_id": state.account_id,
        "tp_price": new_tp
    }
    
    async with httpx.AsyncClient() as client:
        res = await client.put(f"{API_BASE_URL}/execution/positions/{state.market_trade_id}", json=payload, headers=get_headers())
        if res.status_code == 200:
            log_test("Amend Position", True, f"Successfully updated TP to {new_tp}")
        else:
            log_test("Amend Position", False, f"HTTP {res.status_code}: {res.text}")

async def inspect_order(order_id: str):
    print(f"{Fore.CYAN}--- Inspecting Order {order_id} (Human-like Verification) ---{Style.RESET_ALL}")
    async with httpx.AsyncClient() as client:
        print(f"{Fore.YELLOW}⏳ Sleeping 10s to simulate human reaction time...{Style.RESET_ALL}")
        await asyncio.sleep(10)
        
        res = await client.get(f"{API_BASE_URL}/execution/orders", params={"broker_account_id": state.account_id}, headers=get_headers())
        if res.status_code == 200:
            orders = res.json().get("data", [])
            order = next((o for o in orders if str(o.get("id")) == str(order_id)), None)
            if order:
                log_test(f"Inspect Order {order_id}", True, f"Order state: {order.get('status')} Entry: {order.get('price')}")
            else:
                log_test(f"Inspect Order {order_id}", False, "Order not found in pending list.")
        else:
            log_test(f"Inspect Order {order_id}", False, f"HTTP {res.status_code}: {res.text}")

async def test_limit_order():
    print(f"\n{Fore.CYAN}--- P7: REST LIMIT Order + SL/TP (Human-like) ---{Style.RESET_ALL}")
    
    entry_price = round(state.current_ask - 0.01000, 5) # Deep limit
    sl_price = round(entry_price - 0.0050, 5)
    tp_price = round(entry_price + 0.0050, 5)
    
    payload = {
        "broker_account_id": state.account_id,
        "trade_id": str(uuid.uuid4()),
        "symbol": SYMBOL_RAW,
        "order_type": "LIMIT",
        "units": float(LOTS * 100000),
        "price": float(entry_price),
        "sl_price": float(sl_price),
        "tp_price": float(tp_price)
    }
    
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{API_BASE_URL}/execution/orders", json=payload, headers=get_headers())
        if res.status_code == 200:
            data = res.json().get("data", {})
            if "id" in data:
                state.limit_order_id = data["id"]
                log_test("LIMIT Order", True, f"Placed at {entry_price}. ID: {state.limit_order_id}")
                await inspect_order(state.limit_order_id)
            else:
                log_test("LIMIT Order", False, f"No ID: {data}")
        else:
            log_test("LIMIT Order", False, f"HTTP {res.status_code}: {res.text}")

async def test_amend_order():
    print(f"\n{Fore.CYAN}--- P8: REST Amend (Pending Order) ---{Style.RESET_ALL}")
    
    new_entry = round(state.current_ask - 0.01100, 5) 
    
    payload = {
        "broker_account_id": state.account_id,
        "price": float(new_entry)
    }
    
    async with httpx.AsyncClient() as client:
        res = await client.put(f"{API_BASE_URL}/execution/orders/{state.limit_order_id}", json=payload, headers=get_headers())
        if res.status_code == 200:
            data = res.json().get("data", {})
            if "order_id" in data:
                state.limit_order_id = data["order_id"]
            log_test("Amend Order", True, f"Amended entry to {new_entry}. New Order ID: {state.limit_order_id}")
        else:
            log_test("Amend Order", False, f"HTTP {res.status_code}: {res.text}")

async def test_cancel_order():
    print(f"\n{Fore.CYAN}--- P9: REST Cancel Order ---{Style.RESET_ALL}")
    
    async with httpx.AsyncClient() as client:
        res = await client.delete(f"{API_BASE_URL}/execution/orders/{state.limit_order_id}", params={"broker_account_id": state.account_id}, headers=get_headers())
        if res.status_code == 200:
            log_test("Cancel Order", True, f"Order {state.limit_order_id} cancelled.")
        else:
            log_test("Cancel Order", False, f"HTTP {res.status_code}: {res.text}")

async def test_trailing_stop():
    print(f"\n{Fore.CYAN}--- P10: Trailing Stop (Position) ---{Style.RESET_ALL}")
    
    # 1. Enable Trailing Stop
    payload = {
        "broker_account_id": state.account_id,
        "trailing_sl": True
    }
    
    async with httpx.AsyncClient() as client:
        res = await client.put(f"{API_BASE_URL}/execution/positions/{state.market_trade_id}", json=payload, headers=get_headers())
        if res.status_code == 200:
            log_test("Enable Trailing Stop", True, "Successfully ENABLED Trailing Stop Loss")
        else:
            log_test("Enable Trailing Stop", False, f"HTTP {res.status_code}: {res.text}")
            return

        # 2. Verify status
        print(f"{Fore.YELLOW}⏳ Sleeping 5s for broker sync...{Style.RESET_ALL}")
        await asyncio.sleep(5)
        
        res = await client.post(f"{API_BASE_URL}/execution/trades/open", json={"broker_account_id": state.account_id}, headers=get_headers())
        if res.status_code == 200:
            trades = res.json().get("data", [])
            trade = next((t for t in trades if str(t.get("id")) == str(state.market_trade_id) or str(t.get("broker_trade_id")) == str(state.market_trade_id)), None)
            # Adapters return trailing_sl as key, but we are moving to trailing_stop
            status = trade.get("trailing_stop") if trade and "trailing_stop" in trade else trade.get("trailing_sl") if trade else None
            
            if status is True:
                log_test("Verify Trailing SL", True, "Confirmed status is True in live state.")
            else:
                log_test("Verify Trailing SL", False, f"Status mismatch or field missing: {status}")
        
        # 3. Disable Trailing Stop
        payload["trailing_sl"] = False
        res = await client.put(f"{API_BASE_URL}/execution/positions/{state.market_trade_id}", json=payload, headers=get_headers())
        if res.status_code == 200:
            log_test("Disable Trailing Stop", True, "Successfully DISABLED Trailing Stop Loss")
        else:
            log_test("Disable Trailing Stop", False, f"HTTP {res.status_code}: {res.text}")

async def run_suite():
    try:
        # P1-P2: Auth and Account
        await authenticate()
        await get_account()
        
        # Enable Janitor for verification
        async with httpx.AsyncClient() as client:
            await client.put(
                f"{API_BASE_URL}/settings/preferences",
                json={"ctrader_janitor_enabled": True, "oanda_janitor_enabled": True},
                headers=get_headers()
            )
        log_test("Init Prefs", True, "Janitor enabled for OANDA/CTRADER")
        
        # P3: WS
        await test_websocket()
        await asyncio.sleep(1)
        
        # P4: Market Order
        await test_market_order()
        await asyncio.sleep(5) 
        
        # P5: Amend Position
        if state.market_trade_id:
            await test_amend_position()
            await asyncio.sleep(5)
            await inspect_trade(state.market_trade_id)
            
            # P10: Trailing Stop
            await test_trailing_stop()
            await asyncio.sleep(5)
            await inspect_trade(state.market_trade_id)
        
        # P7: Limit Order
        await test_limit_order()
        await asyncio.sleep(5)
        
        # P8: Amend Order
        if state.limit_order_id:
            await test_amend_order()
            await asyncio.sleep(5)
            await inspect_order(state.limit_order_id)
        
        # P9: Cancel Order
        if state.limit_order_id:
            await test_cancel_order()
        
        print(f"\n{Fore.GREEN}🎉 Olympus E2E Integration Suite Completed for cTrader! (Trades LEFT OPEN for inspection){Style.RESET_ALL}")
        
    except Exception as e:
         print(f"{Fore.RED}🚨 Fatal Error executing E2E suite: {e}{Style.RESET_ALL}")
         import traceback
         traceback.print_exc()

if __name__ == "__main__":
    print("Starting Olympus Gateway cTrader E2E Tester...")
    asyncio.run(run_suite())
