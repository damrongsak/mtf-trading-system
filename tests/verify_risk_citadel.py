import requests
import json

BASE_URL = "http://localhost:8003/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0cmFkZXIxIiwiZXhwIjoxNzc0NzU1MjYxfQ.-iP7vaHeiGbyK74TmWXFUCiiHl6Y6QAcfz_NvShIXX8"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def check_risk(scenario_name, payload):
    print(f"\n--- Scenario: {scenario_name} ---")
    url = f"{BASE_URL}/risk/check"
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            data = result.get("data", {})
            print(f"Direction: {data.get('direction')}")
            print(f"RRR: {data.get('risk_reward_ratio')}")
            print(f"Position Size: {data.get('position_size', {}).get('units')} units ({data.get('position_size', {}).get('lots')} lots)")
            print(f"Safe: {data.get('is_safe')}")
            if data.get('warnings'):
                print(f"Warnings: {data.get('warnings')}")
            return data.get('is_safe')
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {str(e)}")
        return False

def run_tests():
    print("===== Risk Citadel (L4) Verification =====")
    
    success_count = 0
    
    # 1. Valid Long (XAUUSD)
    # Entry: 2600, SL: 2590 ($10 risk per oz), TP: 2630 ($30 profit per oz)
    # Risk: $1000, Balance: $100,000 (1%)
    # RRR: 3.0, Units: 100, Lots: 1.0 (since standard lot for GOLD is 100)
    sc1 = {
        "symbol": "XAUUSD",
        "entry_price": 2600.0,
        "stop_loss": 2590.0,
        "take_profit": 2630.0,
        "account_balance": 100000.0,
        "risk_percentage": 1.0
    }
    if check_risk("Valid Long XAUUSD", sc1): success_count += 1
    
    # 2. Poor RRR (RRR < 1.0)
    # Entry: 2600, SL: 2590, TP: 2605
    # RRR: 0.5, should be is_safe: False
    sc2 = {
        "symbol": "XAUUSD",
        "entry_price": 2600.0,
        "stop_loss": 2590.0,
        "take_profit": 2605.0,
        "account_balance": 100000.0
    }
    if not check_risk("Poor RRR (Rejection)", sc2): success_count += 1
    
    # 3. Valid Short (RRR > 1.5)
    # Entry: 2600, SL: 2610, TP: 2570
    # RRR: 3.0, should be is_safe: True
    sc3 = {
        "symbol": "XAUUSD",
        "entry_price": 2600.0,
        "stop_loss": 2610.0,
        "take_profit": 2570.0,
        "risk_usd": 500.0 # Override 1%
    }
    if check_risk("Valid Short XAUUSD", sc3): success_count += 1

    print(f"\nFinal Result: {success_count}/3 Scenarios Passed")

if __name__ == "__main__":
    run_tests()
