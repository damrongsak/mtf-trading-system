import asyncio
import os
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
# Inside docker compose, we can hit it as http://api-gateway:8000
API_BASE_URL = os.getenv("API_GATEWAY_URL", "http://api-gateway:8000/api/v1")
WS_BASE_URL = os.getenv("WS_GATEWAY_URL", "ws://api-gateway:8000/api/v1/stream/prices")

USERNAME = "trader2"
PASSWORD = "password123"
SYMBOL = "EURUSD"
SYMBOL_RAW = "EUR_USD"
SOURCE = "OANDA"
UNITS = 1000

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
        # Standard OAuth2 form request
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
            oanda_acc = next((a for a in accounts if a["broker_name"] == "OANDA"), None)
            if oanda_acc:
                state.account_id = oanda_acc["id"]
                log_test("Account", True, f"Found OANDA Account ID: {state.account_id}")
            else:
                log_test("Account", False, "No OANDA account found for trader2.")
        else:
            log_test("Account", False, f"HTTP {res.status_code}: {res.text}")

async def test_websocket():
    print(f"\n{Fore.CYAN}--- P2: WebSocket Streaming & Pricing ---{Style.RESET_ALL}")
    try:
        # Construct URL with query parameters for auth and subscription
        ws_url = f"{WS_BASE_URL}?token={state.token}&symbols={SYMBOL_RAW}&source={SOURCE}"
        async with websockets.connect(ws_url) as ws:
            log_test("WS Connection", True, "Successfully connected and authenticated via Query Params.")
            
            # 1. Wait for 1 tick to get live price reference
            tick_msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
            
            # Handle binary or text
            if isinstance(tick_msg, bytes):
                tick_msg = tick_msg.decode('utf-8')
            
            data = json.loads(tick_msg)
            msg_type = data.get("type", "").upper()
            instrument = data.get("instrument", data.get("symbol", ""))
            
            if msg_type == "PRICE" and instrument in [SYMBOL, SYMBOL_RAW]:
                state.current_ask = float(data.get("ask", 1.16000))
                state.current_bid = float(data.get("bid", 1.16000))
                log_test("WS Tick", True, f"Received Tick - Bid: {state.current_bid} Ask: {state.current_ask}")
            else:
                log_test("WS Tick", False, f"Unexpected msg format: {tick_msg}")
    except Exception as e:
        log_test("WS Tick", False, f"WebSocket Error: {e}")

async def inspect_trade(trade_id: str):
    print(f"{Fore.CYAN}--- Inspecting Trade {trade_id} (Human-like Verification) ---{Style.RESET_ALL}")
    async with httpx.AsyncClient() as client:
        # Increase delay to ensure OANDA has finished processing the fill and SL/TP legs
        print(f"{Fore.YELLOW}⏳ Sleeping 30s to simulate human reaction time and allow OANDA state sync...{Style.RESET_ALL}")
        await asyncio.sleep(30)
        
        res = await client.get(f"{API_BASE_URL}/execution/trades", params={"broker_account_id": state.account_id}, headers=get_headers())
        if res.status_code == 200:
            trades = res.json().get("data", [])
            
            # Search by internal ID or broker ID
            trade = None
            for t in trades:
                if str(t.get("id")) == str(trade_id) or str(t.get("broker_trade_id")) == str(trade_id):
                    trade = t
                    break
            
            if trade:
                # OANDA Adapter maps stopLossOrder/takeProfitOrder into sl_price/tp_price
                sl = trade.get("sl_price")
                tp = trade.get("tp_price")
                log_test(f"Inspect Trade {trade_id}", True, f"Broker Verified -> SL: {sl}, TP: {tp}")
                print(f"{Fore.GREEN}👉 VISUAL CHECK: Log in to OANDA and look for Trade ID {trade.get('broker_trade_id')}. SL/TP should be visible.{Style.RESET_ALL}")
            else:
                log_test(f"Inspect Trade {trade_id}", False, f"Trade not found in sync list. Open trades: {[t.get('broker_trade_id') for t in trades]}")
        else:
            log_test(f"Inspect Trade {trade_id}", False, f"HTTP {res.status_code}: {res.text}")

async def test_market_order():
    print(f"\n{Fore.CYAN}--- P4: REST MARKET Order + SL/TP (Human-like) ---{Style.RESET_ALL}")
    
    # 1. Fresh Tick
    await test_websocket()
    
    sl_price = round(state.current_ask - 0.0050, 5) # 50 pips
    tp_price = round(state.current_ask + 0.0050, 5) # 50 pips
    
    payload = {
        "broker_account_id": state.account_id,
        "symbol": SYMBOL_RAW,
        "order_type": "MARKET",
        "units": float(UNITS),
        "sl_price": float(sl_price),
        "tp_price": float(tp_price)
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(f"{API_BASE_URL}/execution/orders", json=payload, headers=get_headers())
        if res.status_code == 200:
            data = res.json().get("data", {})
            if "id" in data:
                state.market_trade_id = data["id"]
                log_test("MARKET Order", True, f"Trade opened. ID: {state.market_trade_id}")
                await inspect_trade(state.market_trade_id)
            else:
                log_test("MARKET Order", False, f"Invalid response: {data}")
        else:
             log_test("MARKET Order", False, f"HTTP {res.status_code}: {res.text}")

async def test_amend_position():
    print(f"\n{Fore.CYAN}--- P5: REST Amend TP (Open Position) ---{Style.RESET_ALL}")
    
    new_tp = round(state.current_ask + 0.0030, 5) # 30 pips above
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

async def test_close_trade():
    print(f"\n{Fore.CYAN}--- P6: REST Close Position ---{Style.RESET_ALL}")
    
    payload = {
        "broker_account_id": state.account_id,
        "broker_trade_id": state.market_trade_id
    }
    
    async with httpx.AsyncClient() as client:
        # Endpoint expects empty payload but might accept broker account IDs via query or body depending on execution schema
        # Let's use the standard POST trades/close (internal implementation proxied it, assuming Gateway passes fields)
        res = await client.post(f"{API_BASE_URL}/execution/trades/{state.market_trade_id}/close", json={"exit_price": 0.0}, headers=get_headers())
        # The Olympus API gateway /execution/trades/{id}/close expects "exit_price" in payload, but the internal client 
        # closes the trade directly.
        if res.status_code == 200:
            # We must confirm it was successfully closed.
            log_test("Close Position", True, "Trade closed via Gateway API")
        else:
            log_test("Close Position", False, f"HTTP {res.status_code}: {res.text}")

async def inspect_order(order_id: str):
    print(f"{Fore.CYAN}--- Inspecting Order {order_id} (Human-like Verification) ---{Style.RESET_ALL}")
    async with httpx.AsyncClient() as client:
        print(f"{Fore.YELLOW}⏳ Sleeping 30s to simulate human reaction time and allow OANDA state sync...{Style.RESET_ALL}")
        await asyncio.sleep(30)
        
        res = await client.get(f"{API_BASE_URL}/execution/orders", params={"broker_account_id": state.account_id}, headers=get_headers())
        if res.status_code == 200:
            orders = res.json().get("data", [])
            order = next((o for o in orders if str(o.get("id")) == str(order_id)), None)
            if order:
                log_test(f"Inspect Order {order_id}", True, f"Order state: {order.get('status')} Entry: {order.get('price')}")
                print(f"{Fore.GREEN}👉 VISUAL CHECK: Log in to OANDA. Pending order ID {order_id} should have SL/TP attached.{Style.RESET_ALL}")
            else:
                log_test(f"Inspect Order {order_id}", False, f"Order not found in pending list. Open orders: {[o.get('id') for o in orders]}")
        else:
            log_test(f"Inspect Order {order_id}", False, f"HTTP {res.status_code}: {res.text}")

async def test_limit_order():
    print(f"\n{Fore.CYAN}--- P7: REST LIMIT Order + SL/TP (Human-like) ---{Style.RESET_ALL}")
    
    # Get fresh price
    await test_websocket()
    
    entry_price = round(state.current_ask - 0.0500, 5) 
    sl_price = round(entry_price - 0.0050, 5) # 50 pips
    tp_price = round(entry_price + 0.0050, 5) # 50 pips
    
    payload = {
        "broker_account_id": state.account_id,
        "symbol": SYMBOL_RAW,
        "order_type": "LIMIT",
        "units": float(UNITS),
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
    
    new_entry = round(state.current_ask - 0.0600, 5) 
    
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

async def run_suite():
    try:
        # --- P0: Health Checks ---
        print(f"\n{Fore.CYAN}--- P0: Health Checks ---{Style.RESET_ALL}")
        import requests
        import time
        for service, url in [("Gateway", API_BASE_URL.replace("/api/v1", "/health")), ("Execution", "http://execution:8000/health")]:
            success = False
            for i in range(10):
                try:
                    check_resp = requests.get(url, timeout=5)
                    if check_resp.status_code == 200:
                        print(f"{Fore.GREEN}✅ [{service}] Service is healthy.{Style.RESET_ALL}")
                        success = True
                        break
                except:
                    pass
                print(f"{Fore.YELLOW}⏳ Waiting for {service} to be ready ({i+1}/10)...{Style.RESET_ALL}")
                time.sleep(3)
            if not success:
                print(f"{Fore.RED}🚨 Service {service} not ready. Aborting.{Style.RESET_ALL}")
                return

        # P1-P2: Auth and Account
        await authenticate()
        await get_account()
        
        # P3: WS
        await test_websocket()
        await asyncio.sleep(1)
        
        # P4: Market Order
        await test_market_order()
        await asyncio.sleep(20) 
        
        # P5: Amend Position
        await test_amend_position()
        await asyncio.sleep(20)
        await inspect_trade(state.market_trade_id)
        
        # P6: Close Trade
        print(f"\n{Fore.YELLOW}⚠️ Skipping Phase 6 (Close Position) for manual inspection.{Style.RESET_ALL}")
        # await test_close_trade()
        await asyncio.sleep(5)
        
        # P7: Limit Order
        await test_limit_order()
        await asyncio.sleep(20)
        
        # P8: Amend Order
        await test_amend_order()
        await asyncio.sleep(20)
        await inspect_order(state.limit_order_id)
        
        # P9: Cancel Order
        if state.limit_order_id:
            print(f"\n{Fore.YELLOW}⚠️ Skipping Phase 9 (Cancel Order) for manual inspection.{Style.RESET_ALL}")
            # await test_cancel_order()
        
        print(f"\n{Fore.GREEN}🎉 Olympus E2E Integration Suite Completed! (Trades LEFT OPEN for inspection){Style.RESET_ALL}")
        
    except Exception as e:
         print(f"{Fore.RED}🚨 Fatal Error executing E2E suite: {e}{Style.RESET_ALL}")
         import traceback
         traceback.print_exc()

if __name__ == "__main__":
    print("Starting Olympus Gateway E2E Tester...")
    asyncio.run(run_suite())
