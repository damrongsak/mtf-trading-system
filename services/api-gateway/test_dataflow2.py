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
            "config_json": {
                "logic_blocks": [
                    {
                        "id": "STRUCT_SMC_OB",
                        "parameters": {"timeframe": "15m", "required_direction": "BEARISH"}
                    },
                    {
                        "id": "FILTER_GAMMA_REGIME",
                        "parameters": {"regime": "NEGATIVE_GAMMA", "strict": False}
                    }
                ]
            }
        }
    }

    r = httpx.post(assemble_url, headers=headers, json=payload, timeout=5.0)
    print("Status Code:", r.status_code)
    print("Response JSON:", json.dumps(r.json(), indent=2))

if __name__ == "__main__":
    run_test()
