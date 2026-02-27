import httpx
import json

def run_test():
    # 1. Login
    login_url = "http://localhost:8000/api/v1/auth/token"
    login_data = {"username": "trader1", "password": "password123"}
    print(f"Logging in to {login_url}...")
    try:
        resp = httpx.post(login_url, data=login_data, timeout=5.0)
        resp.raise_for_status()
        token = resp.json().get("auth", {}).get("access_token")
        if not token:
            print("Token not found in response:", resp.json())
            return
        print("Login successful.")
    except Exception as e:
        print("Login failed:", str(e))
        return

    # 2. Test /api/v1/foundry/assemble
    assemble_url = "http://localhost:8000/api/v1/foundry/assemble"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "config": {
            "name": "SMC Gamma Test",
            "description": "Test SMC strategy",
            "version": "1.0",
            "is_active": False,
             "symbol_id": "00000000-0000-0000-0000-000000000000",
             "timeframe": "15m",
             "data_source_id": "00000000-0000-0000-0000-000000000000",
            "components": [
                {
                    "type": "indicator",
                    "name": "smc",
                    "params": {"ob": "bearish", "sweep": True}
                },
                {
                    "type": "filter",
                    "name": "gamma_filter",
                    "params": {"regime": "NEGATIVE_GAMMA"}
                }
            ],
            "execution": {"risk_per_trade": 0.01}
        }
    }

    print(f"\nSending request to {assemble_url}...")
    try:
        r = httpx.post(assemble_url, headers=headers, json=payload, timeout=5.0)
        print("Status Code:", r.status_code)
        print("Response JSON:", json.dumps(r.json(), indent=2))
        
        if r.status_code == 200:
            print("\n✅ Test Passed: Endpoint returned 200 OK without ValidationError.")
        else:
            print("\n❌ Test Failed: Endpoint returned an error status code.")
    except Exception as e:
         print("Request failed:", str(e))

if __name__ == "__main__":
    run_test()
