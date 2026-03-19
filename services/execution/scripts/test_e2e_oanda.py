import asyncio
import os
import sys
import httpx

# Common ANSI colors manually to avoid dependencies
class Fore:
    GREEN = '\033[92m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    YELLOW = '\033[93m'

class Style:
    RESET_ALL = '\033[0m'

# Required Environment Variables
OANDA_API_KEY = os.getenv("OANDA_API_KEY")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
OANDA_ENV = os.getenv("OANDA_ENV", "practice").lower()

if not OANDA_API_KEY or not OANDA_ACCOUNT_ID:
    print(f"{Fore.RED}ERROR: OANDA credentials missing from environment. Tests aborted.{Style.RESET_ALL}")
    sys.exit(1)

# API Host
if OANDA_ENV == "live":
    API_URL = "https://api-fxtrade.oanda.com/v3"
else:
    API_URL = "https://api-fxpractice.oanda.com/v3"

HEADERS = {
    "Authorization": f"Bearer {OANDA_API_KEY}",
    "Content-Type": "application/json"
}

# Configuration
SYMBOL = "EUR_USD"
UNITS = 1000

class State:
    current_bid = 0.0
    current_ask = 0.0
    market_trade_id = None
    limit_order_id = None

state = State()

def log_test(step: str, result: bool, details: str = ""):
    status_color = Fore.GREEN if result else Fore.RED
    status_icon = "✅" if result else "❌"
    print(f"{status_color}{status_icon} [{step}] {details}{Style.RESET_ALL}")
    if not result:
        print(f"{Fore.YELLOW}Aborting subsequent tests due to failure.{Style.RESET_ALL}")
        sys.exit(1)

async def check_permissions():
    """Verify Account and Balance before testing."""
    print(f"{Fore.CYAN}\n--- Initializing OANDA E2E Suite ({OANDA_ENV.upper()}) ---{Style.RESET_ALL}")
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{API_URL}/accounts/{OANDA_ACCOUNT_ID}/summary", headers=HEADERS)
        if res.status_code != 200:
            log_test("Account Verification", False, f"Failed: {res.text}")
        
        data = res.json()
        balance = float(data['account']['balance'])
        
        print(f"💰 Account Balance: ${balance:.2f}")
        if balance < 10.0:
            log_test("Balance Check", False, f"Insufficient funds ($ {balance}) to run E2E test safely.")
        else:
            log_test("Initialization", True, "Account OK. Proceeding with E2E tests...")

async def get_live_price():
    """Test 1: Fetch Live Price"""
    print(f"\n{Fore.CYAN}--- Test 1: Get Live Price ---{Style.RESET_ALL}")
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{API_URL}/accounts/{OANDA_ACCOUNT_ID}/pricing?instruments={SYMBOL}", headers=HEADERS)
        if res.status_code == 200:
            data = res.json()
            if data.get('prices'):
                price = data['prices'][0]
                state.current_bid = float(price['bids'][0]['price'])
                state.current_ask = float(price['asks'][0]['price'])
                log_test("Get Live Price", True, f"Bid: {state.current_bid}, Ask: {state.current_ask}")
            else:
                log_test("Get Live Price", False, "No price data returned.")
        else:
            log_test("Get Live Price", False, f"API Error HTTP {res.status_code}")

async def test_market_order():
    """Test 2: Place MARKET Order with SL/TP"""
    print(f"\n{Fore.CYAN}--- Test 2: MARKET Order + SL/TP ---{Style.RESET_ALL}")
    
    # Calculate SL and TP around current Ask (Buy Order)
    # EURUSD is 5 decimal places. 1 pip = 0.0001
    sl_price = round(state.current_ask - 0.0020, 5) # 20 pips below
    tp_price = round(state.current_ask + 0.0020, 5) # 20 pips above
    
    payload = {
        "order": {
            "type": "MARKET",
            "instrument": SYMBOL,
            "units": str(UNITS),
            "timeInForce": "FOK",
            "positionFill": "DEFAULT",
            "stopLossOnFill": {
                "timeInForce": "GTC",
                "price": str(sl_price)
            },
            "takeProfitOnFill": {
                "timeInForce": "GTC",
                "price": str(tp_price)
            }
        }
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(f"{API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders", json=payload, headers=HEADERS)
        
        if res.status_code == 201:
            data = res.json()
            # Extract filled trade ID
            if 'orderFillTransaction' in data:
                state.market_trade_id = data['orderFillTransaction']['id']
                fill_price = data['orderFillTransaction']['price']
                log_test("MARKET Order", True, f"Filled at {fill_price} (Trade ID: {state.market_trade_id})")
            else:
                log_test("MARKET Order", False, "Order created but not filled (no orderFillTransaction)")
        else:
            log_test("MARKET Order", False, f"Error: {res.text}")

async def test_amend_open_position():
    """Test 3: Amend SL/TP (Open Position)"""
    print(f"\n{Fore.CYAN}--- Test 3: Amend SL/TP (Open Position) ---{Style.RESET_ALL}")
    
    if not state.market_trade_id:
         log_test("Amend Open Position", False, "No active trade ID available.")
         
    # Update SL/TP slightly
    new_tp = round(state.current_ask + 0.0030, 5) # 30 pips above
    
    payload = {
        "takeProfit": {
            "timeInForce": "GTC",
            "price": str(new_tp)
        }
    }
    
    async with httpx.AsyncClient() as client:
        # Amend trade endpoints use TradeCRCDO extension
        res = await client.put(f"{API_URL}/accounts/{OANDA_ACCOUNT_ID}/trades/{state.market_trade_id}/orders", json=payload, headers=HEADERS)
        
        if res.status_code == 200:
            log_test("Amend Open Position", True, f"Successfully updated TP to {new_tp}")
        else:
            log_test("Amend Open Position", False, f"Error: {res.text}")

async def test_close_position():
    """Test 4: Close Position (Clean up Market Order)"""
    print(f"\n{Fore.CYAN}--- Test 4: Close Position ---{Style.RESET_ALL}")
    
    if not state.market_trade_id:
         log_test("Close Position", False, "No active trade ID available.")
    
    # Close by instrument (simpler for netting accounts, but let's target the specific trade)
    async with httpx.AsyncClient() as client:
        res = await client.put(f"{API_URL}/accounts/{OANDA_ACCOUNT_ID}/trades/{state.market_trade_id}/close", headers=HEADERS)
        
        if res.status_code == 200:
            data = res.json()
            if 'orderFillTransaction' in data:
                pnl = data['orderFillTransaction'].get('pl', '0.00')
                log_test("Close Position", True, f"Trade closed successfully. Realized PnL: {pnl}")
            else:
                 log_test("Close Position", True, "Trade closed (Check UI)")
        else:
            log_test("Close Position", False, f"Error: {res.text}")

async def test_limit_order():
    """Test 5: Place LIMIT Order + SL/TP"""
    print(f"\n{Fore.CYAN}--- Test 5: LIMIT Order + SL/TP ---{Style.RESET_ALL}")
    
    # Place it far away so it doesn't fill
    entry_price = round(state.current_ask - 0.0500, 5) # 500 pips below
    sl_price = round(entry_price - 0.0020, 5)
    tp_price = round(entry_price + 0.0020, 5)
    
    payload = {
        "order": {
            "type": "LIMIT",
            "instrument": SYMBOL,
            "units": str(UNITS),
            "price": str(entry_price),
            "timeInForce": "GTC",
            "positionFill": "DEFAULT",
            "stopLossOnFill": {
                "timeInForce": "GTC",
                "price": str(sl_price)
            },
            "takeProfitOnFill": {
                "timeInForce": "GTC",
                "price": str(tp_price)
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders", json=payload, headers=HEADERS)
        
        if res.status_code == 201:
            data = res.json()
            if 'orderCreateTransaction' in data:
                state.limit_order_id = data['orderCreateTransaction']['id']
                log_test("LIMIT Order", True, f"Placed at {entry_price} (Order ID: {state.limit_order_id})")
            else:
                log_test("LIMIT Order", False, "Response successful, but no order ID found.")
        else:
            log_test("LIMIT Order", False, f"Error: {res.text}")

async def test_amend_pending_order():
    """Test 6: Amend Pending Order"""
    print(f"\n{Fore.CYAN}--- Test 6: Amend Pending Order ---{Style.RESET_ALL}")
    
    if not state.limit_order_id:
         log_test("Amend Pending Order", False, "No active limit order ID available.")
    
    # Update Entry Price
    new_entry = round(state.current_ask - 0.0600, 5) # 600 pips below now
    
    payload = {
        "order": {
            "type": "LIMIT",
            "instrument": SYMBOL,
            "units": str(UNITS),
            "price": str(new_entry),
            "timeInForce": "GTC"
        }
    }
    
    async with httpx.AsyncClient() as client:
        # Amend order uses PUT /orders/{id}
        res = await client.put(f"{API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders/{state.limit_order_id}", json=payload, headers=HEADERS)
        
        if res.status_code == 201: # OANDA returns 201 Created for order replacement
            data = res.json()
            if 'orderCreateTransaction' in data:
                 new_order_id = data['orderCreateTransaction']['id']
                 log_test("Amend Pending Order", True, f"Successfully amended entry to {new_entry}. New Order ID: {new_order_id}")
                 # Update state with new ID
                 state.limit_order_id = new_order_id
            else:
                 log_test("Amend Pending Order", True, "Amended successfully.")
        else:
            log_test("Amend Pending Order", False, f"Error: {res.text}")

async def test_cancel_order():
    """Test 7: Cancel Order"""
    print(f"\n{Fore.CYAN}--- Test 7: Cancel Order ---{Style.RESET_ALL}")
    
    if not state.limit_order_id:
         log_test("Cancel Order", False, "No active limit order ID available to cancel.")

    async with httpx.AsyncClient() as client:
        res = await client.put(f"{API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders/{state.limit_order_id}/cancel", headers=HEADERS)
        
        if res.status_code == 200:
            log_test("Cancel Order", True, f"Order {state.limit_order_id} cancelled successfully.")
        else:
            log_test("Cancel Order", False, f"Error: {res.text}")

async def run_suite():
    try:
        await check_permissions()
        await get_live_price()
        
        # Test 2, 3, 4 (Market lifecycle)
        await asyncio.sleep(1)
        await test_market_order()
        await asyncio.sleep(2) # Give OANDA time to process FILL
        await test_amend_open_position()
        await asyncio.sleep(2)
        await test_close_position()
        
        # Test 5, 6, 7 (Pending lifecycle)
        await asyncio.sleep(2)
        await test_limit_order()
        await asyncio.sleep(2)
        await test_amend_pending_order()
        await asyncio.sleep(2)
        await test_cancel_order()
        
        print(f"\n{Fore.GREEN}🎉 E2E OANDA Suite Completed Successfully!{Style.RESET_ALL}")
        
    except Exception as e:
         print(f"{Fore.RED}🚨 Fatal Error executing E2E suite: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    print("Starting E2E Tester...")
    asyncio.run(run_suite())
