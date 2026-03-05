import requests
import time
import math
import os
import uuid
import json
from datetime import datetime

# --- CONFIGURATION ---
BASE_URL = os.getenv("OLYMPUS_API_URL", "http://localhost:8000")
USERNAME = os.getenv("OLYMPUS_USERNAME", "trader1")
PASSWORD = os.getenv("OLYMPUS_PASSWORD", "password123")
SYMBOL = "XAU_USD"
BROKER_ACCOUNT_ID = os.getenv("BROKER_ACCOUNT_ID", "4438a19e-5d19-48c9-89d6-5134ee996591")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

def print_header(text):
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)

def main():
    print_header("E2E Test: Soda -> Olympus -> Broker (LIMIT Order)")

    # [1/4] Authenticating...
    print("[1/4] Authenticating...")
    auth_url = f"{BASE_URL}/api/v1/auth/token"
    try:
        resp = requests.post(auth_url, data={
            "username": USERNAME,
            "password": PASSWORD
        }, timeout=10)
        resp.raise_for_status()
        auth_data = resp.json()
        token = auth_data.get("auth", {}).get("access_token")
        if not token:
            print("    ❌ Failed to extract token from response")
            return
        print("    ✅ Token obtained")
    except Exception as e:
        print(f"    ❌ Auth failed: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # [2/4] Fetching market data...
    print("[2/4] Fetching market data...")
    # Using candles to calculate ATR
    candles_url = f"{BASE_URL}/api/v1/market/candles?symbol=XAUUSD&timeframe=M15&limit=20"
    try:
        resp = requests.get(candles_url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # Handle both wrapped and unwrapped responses
        candles = data.get("data", data) if isinstance(data, dict) else data
        if not candles:
            print("    ❌ No candles returned")
            return
        
        current_price = candles[-1]["close"]
        
        # Simple ATR(14) calculation
        tr_list = []
        for i in range(1, len(candles)):
            h = candles[i]["high"]
            l = candles[i]["low"]
            pc = candles[i-1]["close"]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            tr_list.append(tr)
        
        atr = sum(tr_list[-14:]) / 14 if len(tr_list) >= 14 else sum(tr_list) / len(tr_list)
        
        print(f"    Current Price: {current_price:.2f}")
        print(f"    ATR (approx): {atr:.2f}")
    except Exception as e:
        print(f"    ❌ Market data failed: {e}")
        return

    # [3/4] Calculating safe entry (BUY)...
    print("[3/4] Calculating safe entry (BUY)...")
    
    # 5 ATR offset to ensure the limit order is "safe" (not filled immediately)
    entry_price = round(current_price - (5 * atr), 2)
    stop_loss = round(entry_price - (2 * atr), 2)
    take_profit = round(entry_price + (6 * atr), 2)
    
    risk_pips = entry_price - stop_loss
    reward_pips = take_profit - entry_price
    rrr = reward_pips / risk_pips if risk_pips > 0 else 0
    
    print(f"    Entry (LIMIT): {entry_price:.2f}  (market - 5 ATR)")
    print(f"    Stop Loss:     {stop_loss:.2f}  (2 ATR risk)")
    print(f"    Take Profit:   {take_profit:.2f}  (6 ATR reward)")
    print(f"    Risk:Reward = 1:{rrr:.1f} {'✅' if rrr >= 1.5 else '⚠️'}")

    # [4/4] Sending Payload
    # Map to Execution Service schema
    payload = {
        "broker_account_id": BROKER_ACCOUNT_ID,
        "symbol": SYMBOL,
        "order_type": "LIMIT",
        "units": 0.01,  # positive = BUY
        "price": entry_price,
        "sl_price": stop_loss,
        "tp_price": take_profit,
        "comment": f"e2e_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    }
    
    print("\nPayload:")
    print(json.dumps(payload, indent=2))

    if DRY_RUN:
        print("\n    🟡 DRY RUN - No order sent")
        return

    print("\nExecuting order...")
    exec_url = f"{BASE_URL}/api/v1/execution/orders"
    try:
        resp = requests.post(exec_url, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        print(f"    ✅ Success: {json.dumps(result.get('data', {}), indent=2)}")
    except Exception as e:
        print(f"    ❌ Execution failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"    Response: {e.response.text}")

if __name__ == "__main__":
    main()
