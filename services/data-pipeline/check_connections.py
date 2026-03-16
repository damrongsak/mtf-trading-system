import requests
import json
import os

API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://api-gateway:8000/api/v1")
EXECUTION_URL = os.getenv("EXECUTION_URL", "http://execution:8000")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev_secret_key")

# Test users for verification (can be overridden via env)
USERS = json.loads(os.getenv("VERIFY_USERS", '[{"username": "trader1", "password": "password123"}, {"username": "trader2", "password": "password123"}, {"username": "demo1", "password": "password123"}]'))

# Critical accounts mapping (can be overridden via env)
BROKER_ACCOUNTS = json.loads(os.getenv("VERIFY_ACCOUNTS", '{"CTRADER": "ae8d4499-c90d-43f6-b14a-d5697dd4c799", "OANDA": "53e48543-7f6f-465c-ac20-d23d2d2b5495", "ICMARKETSSC": "066e21a0-0933-4f70-8e35-605f4759f927"}'))

def login(username, password):
    url = f"{API_GATEWAY_URL}/auth/token"
    data = {"username": username, "password": password}
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            res_json = response.json()
            if "auth" in res_json and "access_token" in res_json["auth"]:
                return res_json["auth"]["access_token"]
            elif "access_token" in res_json:
                return res_json["access_token"]
            return None
        else:
            print(f"  [FAIL] Login for {username} failed with status {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"  [ERROR] Login for {username} error: {e}")
        return None

def check_broker_account(account_id):
    url = f"{EXECUTION_URL}/account/summary"
    headers = {"X-Internal-API-Key": INTERNAL_API_KEY}
    payload = {"broker_account_id": account_id}
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return True, response.json().get("data", {})
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)

def main():
    print("=== MTF Olympus Connectivity Report ===")
    
    for user_info in USERS:
        username = user_info["username"]
        print(f"\nUser: {username}")
        token = login(username, user_info["password"])
        
        if token:
            print(f"  [PASS] Login successful")
            
            user_accounts = []
            if username in ["trader1", "trader2"]:
                user_accounts = ["CTRADER", "OANDA"]
            elif username == "demo1":
                user_accounts = ["ICMARKETSSC"]
            
            for broker in user_accounts:
                acc_id = BROKER_ACCOUNTS[broker]
                print(f"  Checking Broker Account: {broker} ({acc_id[:8]}...)")
                success, data = check_broker_account(acc_id)
                if success:
                    balance = data.get("balance", "N/A")
                    nav = data.get("NAV", "N/A")
                    print(f"    [PASS] Connected. Balance: {balance}, NAV: {nav}")
                else:
                    print(f"    [FAIL] Connection Error: {data}")
        else:
            continue

if __name__ == "__main__":
    main()
