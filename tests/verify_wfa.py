import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8003/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0cmFkZXIxIiwiZXhwIjoxNzc0NzU1MjYxfQ.-iP7vaHeiGbyK74TmWXFUCiiHl6Y6QAcfz_NvShIXX8"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_wfa():
    print("--- Testing Walk-Forward Analysis (WFA) ---")
    
    # SMC + Gamma Setup
    config = {
        "logic_blocks": [
            {
                "id": "TREND_EMA_CROSS",
                "name": "EMA_Filter",
                "parameters": {"period": 200, "timeframe": "H4"}
            },
            {
                "id": "FILTER_GAMMA_REGIME",
                "name": "Gamma_Filter",
                "parameters": {"regime": "NEGATIVE_GAMMA", "strict": False}
            }
        ],
        "train_window_days": 10,
        "test_window_days": 5,
        "step_days": 5,
        "optimization": {
            "param_grid": {
                "EMA_Filter_period": [10, 20]
            }
        }
    }

    payload = {
        "symbol": "XAUUSD",
        "timeframe": "H1",
        "start_date": "2026-01-20T00:00:00Z",
        "end_date": "2026-02-27T03:00:00Z",
        "config": config
    }

    url = f"{BASE_URL}/foundry/validate"
    print(f"POST {url}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("WFA Result:")
            print(json.dumps(result, indent=2))
            
            data = result.get("data", {})
            score = data.get("robustness_score", 0)
            print(f"\nRobustness Score: {score}")
            
            if score > 0:
                print("SUCCESS: Proving Ground (WFA) validated.")
            else:
                print("WARNING: WFA executed but score is 0. Check data availability or strategy logic.")
        else:
            print(f"FAILED: {response.text}")
            
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    test_wfa()
