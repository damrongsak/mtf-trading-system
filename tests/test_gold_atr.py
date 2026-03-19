import requests
import json
import time
import subprocess

BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "demo1"
PASSWORD = "password123"

def get_redis_price():
    # Fetch live price from Redis
    cmd = ["docker", "compose", "exec", "redis", "redis-cli", "HGETALL", "market_data:spot:CTRADER:XAUUSD"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, None
    
    lines = result.stdout.strip().split('\n')
    data = {}
    for i in range(0, len(lines), 2):
        if i+1 < len(lines):
            data[lines[i]] = lines[i+1]
    
    return float(data.get('bid', 0)), float(data.get('ask', 0))

def place_gold_atr_order():
    # 1. Login
    print("--- 1. Login ---")
    auth_resp = requests.post(f"{BASE_URL}/auth/token", data={"username": USERNAME, "password": PASSWORD})
    if auth_resp.status_code != 200:
        print(f"Login failed: {auth_resp.text}")
        return
    
    token = auth_resp.json()["auth"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Get Account
    print("--- 2. Get Account ---")
    acc_resp = requests.get(f"{BASE_URL}/execution/accounts", headers=headers)
    accounts = acc_resp.json().get("data", [])
    if not accounts:
        print("No accounts found")
        return
    
    account_id = accounts[0]["id"]
    print(f"Using account: {account_id}")
    
    # 3. Get Live Price & Calculate ATR SL/TP
    # We use ATR=10.0 (points) as calculated from last 20 H1 candles
    ATR = 10.0
    bid, ask = get_redis_price()
    if not ask:
        print("Failed to get live price from Redis")
        return
    
    entry_price = ask
    sl = entry_price - (2 * ATR)
    tp = entry_price + (2.5 * ATR)
    
    print(f"--- 3. Order Details ---")
    print(f"Symbol: XAU_USD")
    print(f"Entry: {entry_price} (Ask)")
    print(f"SL: {sl} (Market - 2*ATR)")
    print(f"TP: {tp} (Market + 2.5*ATR)")
    print(f"Units: 0.01")
    
    # 4. Place Order
    print("--- 4. Place Order ---")
    payload = {
        "broker_account_id": account_id,
        "symbol": "XAU_USD",
        "order_type": "MARKET",
        "units": 0.01,
        "sl_price": round(sl, 2),
        "tp_price": round(tp, 2),
        "comment": "ATR_TEST_BUY"
    }
    
    order_resp = requests.post(f"{BASE_URL}/execution/orders", json=payload, headers=headers)
    print(f"Status: {order_resp.status_code}")
    print(f"Body: {order_resp.text}")
    
    if order_resp.status_code in [200, 201]:
        print("\033[92mSUCCESS: ATR Order Accepted\033[0m")
    else:
        print("\033[91mFAILED: ATR Order Rejected\033[0m")

if __name__ == "__main__":
    place_gold_atr_order()
