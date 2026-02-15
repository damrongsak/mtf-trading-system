import httpx
import asyncio
import os
import sys

API_URL = "http://localhost:8000"
TOKEN = os.getenv("AUTH_TOKEN") # Need a token for verification

async def verify():
    if not TOKEN:
        print("ERROR: AUTH_TOKEN environment variable not set.")
        sys.exit(1)
        
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        # 1. Fetch Broker Accounts to get an ID
        print("\n--- 1. Fetching Broker Accounts ---")
        try:
            resp = await client.get(f"{API_URL}/api/v1/execution/accounts")
            resp.raise_for_status()
            accounts = resp.json().get("data", [])
            if not accounts:
                print("No broker accounts found. Cannot proceed with further tests.")
                return
            
            account_id = accounts[0]['id']
            print(f"Found account: {accounts[0]['broker_name']} ({account_id})")
        except Exception as e:
            print(f"Failed to fetch accounts: {e}")
            return

        # 2. Test GET /orders (Pending Orders)
        print("\n--- 2. Testing GET /api/v1/execution/orders ---")
        try:
            resp = await client.get(f"{API_URL}/api/v1/execution/orders", params={"broker_account_id": account_id})
            resp.raise_for_status()
            orders = resp.json().get("data", [])
            print(f"Success! Found {len(orders)} pending orders.")
        except Exception as e:
            print(f"Failed to fetch orders: {e}")

        # 3. Test POST /api/v1/trades/close-all (Dry run/Check structure)
        print("\n--- 3. Testing POST /api/v1/execution/trades/close-all ---")
        try:
            # We don't want to actually close everything if not needed, 
            # but we can test the endpoint exists.
            # Using a fake symbol to minimize impact if it tries to close
            resp = await client.post(f"{API_URL}/api/v1/execution/trades/close-all", json={
                "broker_account_id": account_id,
                "symbol": "NON_EXISTENT_SYMBOL"
            })
            resp.raise_for_status()
            res = resp.json().get("data", {})
            print(f"Success! Closed count: {res.get('closed_count', 0)}")
        except Exception as e:
            print(f"Failed to close all trades: {e}")

        # 4. Test POST /api/v1/signals/cancel-all (Bulk Reject)
        print("\n--- 4. Testing POST /api/v1/signals/cancel-all ---")
        try:
            resp = await client.post(f"{API_URL}/api/v1/signals/cancel-all")
            resp.raise_for_status()
            res = resp.json().get("data", {})
            print(f"Success! Cancelled {res.get('cancelled', 0)} signals.")
        except Exception as e:
            print(f"Failed to cancel all signals: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
