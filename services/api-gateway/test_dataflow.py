import httpx
import json

def run_test():
    login_url = "http://localhost:8000/api/v1/auth/token"
    login_data = {"username": "trader1", "password": "password123"}
    resp = httpx.post(login_url, data=login_data, timeout=5.0)
    token = resp.json().get("auth", {}).get("access_token")

    assemble_url = "http://localhost:8000/api/v1/foundry/assemble"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "config": {
            "name": "SMC Gamma Test",
            "logic_blocks": [
                {
                    "id": "STRUCT_SMC_OB",
                    "name": "smc_block",
                    "parameters": {"timeframe": "15m", "required_direction": "BEARISH"}
                },
                {
                    "id": "SOME_FILTER", # Deliberately invalid to test what happens
                    "name": "gamma_filter",
                    "parameters": {"regime": "NEGATIVE_GAMMA"}
                }
            ],
            "parameters": {"risk_per_trade": 0.01}
        }
    }

    print("Sending payload:")
    print(json.dumps(payload, indent=2))
    r = httpx.post(assemble_url, headers=headers, json=payload, timeout=5.0)
    print("Status Code:", r.status_code)
    print("Response JSON:", json.dumps(r.json(), indent=2))

if __name__ == "__main__":
    run_test()
